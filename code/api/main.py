"""API do Monitor de Queimadas.

Rodar com: .venv/bin/uvicorn code.api.main:app --port 8010
Documentação interativa: http://localhost:8010/docs
"""

from __future__ import annotations

import csv
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from . import llm

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
API_CSV = RAW_DIR / "focos_api.csv"

app = FastAPI(
    title="API do Monitor de Queimadas",
    description=(
        "Acesso aos focos de calor do INPE e às notícias raspadas pelo projeto. "
        "Aceita o registro de focos complementares e processa textos com "
        "modelos de linguagem locais (sentimento e resumo)."
    ),
    version="2.0",
)


@lru_cache
def carregar_focos() -> pd.DataFrame:
    arquivos = sorted(RAW_DIR.glob("focos_diario_br_*.csv"))
    frames = [pd.read_csv(a) for a in arquivos]
    if API_CSV.exists():
        frames.append(pd.read_csv(API_CSV))
    return pd.concat(frames, ignore_index=True)


@lru_cache
def carregar_noticias() -> pd.DataFrame:
    fontes = {
        "Agência Brasil": RAW_DIR / "noticias_queimadas.csv",
        "G1": RAW_DIR / "noticias_g1.csv",
    }
    frames = []
    for fonte, caminho in fontes.items():
        if caminho.exists():
            df = pd.read_csv(caminho)
            df["fonte"] = fonte
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def como_registros(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


class Foco(BaseModel):
    """Foco de calor complementar enviado por um usuário."""

    lat: float = Field(ge=-90, le=90, description="Latitude em graus decimais")
    lon: float = Field(ge=-180, le=180, description="Longitude em graus decimais")
    estado: str = Field(min_length=2, description="Estado do foco")
    municipio: str = Field(default="", description="Município do foco")
    bioma: str = Field(default="", description="Bioma do foco")
    frp: float | None = Field(default=None, ge=0, description="Intensidade em MW")


class RespostaFocos(BaseModel):
    """Resposta de GET /focos."""

    total_filtrado: int = Field(description="Focos que atendem ao filtro")
    focos: list[dict] = Field(description="Registros retornados, até o limite")


class RespostaNoticias(BaseModel):
    """Resposta de GET /noticias."""

    total: int
    noticias: list[dict]


class RespostaFocoCriado(BaseModel):
    """Resposta de POST /focos."""

    mensagem: str
    foco: dict


class PedidoProcessarTexto(BaseModel):
    """Texto a processar pelo modelo de linguagem local."""

    texto: str = Field(
        min_length=20,
        max_length=20000,
        description="Texto em português com pelo menos 20 caracteres",
    )
    tipo_analise: Literal["sentimento", "resumo"] = Field(
        description="Análise a executar"
    )


class ResultadoSentimento(BaseModel):
    rotulo: Literal["positivo", "neutro", "negativo"]
    confianca: float = Field(ge=0, le=1, description="Confiança do classificador")


class ResultadoResumo(BaseModel):
    resumo: str


class RespostaProcessarTexto(BaseModel):
    """Resposta de POST /processar_texto."""

    tipo_analise: Literal["sentimento", "resumo"]
    modelo: str = Field(description="Modelo HuggingFace executado localmente")
    tempo_segundos: float = Field(description="Duração do processamento")
    resultado: ResultadoSentimento | ResultadoResumo


@app.get("/focos", response_model=RespostaFocos)
def listar_focos(
    estado: str | None = Query(default=None, description="Filtra por estado"),
    bioma: str | None = Query(default=None, description="Filtra por bioma"),
    limite: int = Query(default=100, ge=1, le=1000, description="Máximo retornado"),
):
    """Lista focos de calor, com filtros opcionais por estado e bioma."""
    df = carregar_focos()
    if estado:
        df = df[df["estado"].str.upper() == estado.upper()]
    if bioma:
        df = df[df["bioma"].str.lower() == bioma.lower()]
    return {
        "total_filtrado": len(df),
        "focos": como_registros(df.head(limite)),
    }


@app.get("/noticias", response_model=RespostaNoticias)
def listar_noticias(
    fonte: str | None = Query(default=None, description="Agência Brasil ou G1"),
):
    """Lista as notícias raspadas, com filtro opcional por fonte."""
    df = carregar_noticias()
    if fonte and not df.empty:
        df = df[df["fonte"].str.lower() == fonte.lower()]
    return {"total": len(df), "noticias": como_registros(df)}


@app.post("/focos", status_code=201, response_model=RespostaFocoCriado)
def adicionar_foco(foco: Foco):
    """Registra um foco complementar, somado às respostas de GET /focos."""
    registro = {
        "id": f"api-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "lat": foco.lat,
        "lon": foco.lon,
        "data_hora_gmt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "satelite": "USUARIO",
        "municipio": foco.municipio.upper(),
        "estado": foco.estado.upper(),
        "pais": "Brasil",
        "bioma": foco.bioma,
        "frp": foco.frp,
    }
    novo_arquivo = not API_CSV.exists()
    with API_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(registro))
        if novo_arquivo:
            writer.writeheader()
        writer.writerow(registro)
    carregar_focos.cache_clear()
    return {"mensagem": "foco registrado", "foco": registro}


@app.post("/processar_texto", response_model=RespostaProcessarTexto)
def processar_texto(pedido: PedidoProcessarTexto):
    """Processa um texto com o modelo de linguagem local.

    Com tipo_analise "sentimento", classifica o texto como positivo, neutro ou
    negativo; com "resumo", gera um resumo em português. A primeira chamada de
    cada análise baixa o modelo do HuggingFace e demora mais; as seguintes usam
    o modelo já carregado em memória, sem acesso à rede.
    """
    if not pedido.texto.strip():
        raise HTTPException(
            status_code=400, detail="O texto enviado contém apenas espaços."
        )

    inicio = time.perf_counter()
    try:
        if pedido.tipo_analise == "sentimento":
            resultado = llm.analisar_sentimento(pedido.texto)
            modelo = llm.MODELO_SENTIMENTO
        else:
            resultado = llm.resumir(pedido.texto)
            modelo = llm.MODELO_RESUMO
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Modelo de linguagem indisponível. Verifique se as dependências "
                "(transformers, torch, sentencepiece) estão instaladas e se há "
                "conexão para o primeiro download do modelo. Erro original: "
                f"{exc}"
            ),
        ) from exc

    return {
        "tipo_analise": pedido.tipo_analise,
        "modelo": modelo,
        "tempo_segundos": round(time.perf_counter() - inicio, 2),
        "resultado": resultado,
    }
