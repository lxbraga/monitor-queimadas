"""API do Monitor de Queimadas.

Rodar com: .venv/bin/uvicorn code.api.main:app --port 8010
Documentação interativa: http://localhost:8010/docs
"""

from __future__ import annotations

import csv
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TempoEsgotado
from datetime import datetime, timezone
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .. import base_dados
from . import llm

# Limite para o processamento, contado a partir do início da execução. O
# carregamento do modelo fica de fora porque o primeiro download leva minutos.
TEMPO_LIMITE_SEGUNDOS = 60
# Quanto um pedido espera por um processador livre antes de desistir.
TEMPO_FILA_SEGUNDOS = 30
_executor = ThreadPoolExecutor(max_workers=2)

_trava_csv = threading.Lock()
_cache: dict[str, tuple] = {}

app = FastAPI(
    title="API do Monitor de Queimadas",
    description=(
        "Acesso aos focos de calor do INPE e às notícias raspadas pelo projeto. "
        "Aceita o registro de focos complementares e processa textos com "
        "modelos de linguagem locais (sentimento e resumo)."
    ),
    version="2.0",
)


def _ler_com_cache(nome: str, arquivos: list, ler):
    """Relê os arquivos só quando algum deles mudou desde a última leitura."""
    chave = base_dados.assinatura(arquivos)
    guardado = _cache.get(nome)
    if guardado is None or guardado[0] != chave:
        guardado = (chave, ler())
        _cache[nome] = guardado
    return guardado[1]


def carregar_focos() -> pd.DataFrame:
    arquivos = base_dados.arquivos_focos(incluir_api=True)
    return _ler_com_cache("focos", arquivos, lambda: base_dados.ler_focos(arquivos))


def carregar_noticias() -> pd.DataFrame:
    arquivos = list(base_dados.NOTICIAS_CSV.values())
    return _ler_com_cache("noticias", arquivos, base_dados.ler_noticias)


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


class RespostaSaude(BaseModel):
    """Resposta de GET /saude."""

    status: Literal["ok"]


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
    tokens_entrada: int = Field(description="Tamanho do texto em tokens")
    truncado: bool = Field(
        description=(
            f"True quando o texto passou de {llm.MAX_TOKENS} tokens e só o "
            "começo foi analisado"
        )
    )
    resultado: ResultadoSentimento | ResultadoResumo


class Erro(BaseModel):
    """Corpo das respostas de erro."""

    detail: str = Field(description="Explicação do problema")


RESPOSTAS_ERRO = {
    400: {"model": Erro, "description": "Texto vazio"},
    500: {"model": Erro, "description": "Falha ao processar o texto"},
    503: {
        "model": Erro,
        "description": "Modelo não pôde ser carregado ou está ocupado",
    },
    504: {"model": Erro, "description": "Processamento passou do tempo limite"},
}


@app.get("/saude", response_model=RespostaSaude)
def saude():
    """Responde na hora se a API está no ar, sem ler arquivos nem modelos."""
    return {"status": "ok"}


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
    agora = datetime.now(timezone.utc)
    registro = {
        "id": f"api-{agora.strftime('%Y%m%d%H%M%S%f')}",
        "lat": foco.lat,
        "lon": foco.lon,
        "data_hora_gmt": agora.strftime("%Y-%m-%d %H:%M:%S"),
        "satelite": "USUARIO",
        "municipio": foco.municipio.upper(),
        "estado": foco.estado.upper(),
        "pais": "Brasil",
        "bioma": foco.bioma,
        "frp": foco.frp,
    }
    # Sem a trava, dois primeiros envios simultâneos gravariam o cabeçalho duas vezes.
    with _trava_csv:
        destino = base_dados.FOCOS_API_CSV
        novo_arquivo = not destino.exists()
        with destino.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(registro))
            if novo_arquivo:
                writer.writeheader()
            writer.writerow(registro)
    return {"mensagem": "foco registrado", "foco": registro}


@app.post(
    "/processar_texto",
    response_model=RespostaProcessarTexto,
    responses=RESPOSTAS_ERRO,
)
def processar_texto(pedido: PedidoProcessarTexto):
    """Processa um texto com o modelo de linguagem local.

    Com tipo_analise "sentimento", classifica o texto como positivo, neutro ou
    negativo; com "resumo", gera um resumo em português. A primeira chamada de
    cada análise baixa o modelo do HuggingFace e demora mais; as seguintes usam
    o modelo já carregado em memória, sem acesso à rede. Textos acima de 512
    tokens são cortados, e a resposta avisa pelo campo truncado.
    """
    if not pedido.texto.strip():
        raise HTTPException(
            status_code=400, detail="O texto enviado contém apenas espaços."
        )

    if pedido.tipo_analise == "sentimento":
        processar, modelo = llm.analisar_sentimento, llm.MODELO_SENTIMENTO
    else:
        processar, modelo = llm.resumir, llm.MODELO_RESUMO

    try:
        llm.carregar(pedido.tipo_analise)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Não foi possível carregar o modelo {modelo}. Verifique se as "
                "dependências (transformers, torch, sentencepiece) estão "
                "instaladas e se há conexão para o primeiro download. "
                f"Erro original: {exc}"
            ),
        ) from exc

    comecou = threading.Event()

    def executar():
        comecou.set()
        return processar(pedido.texto)

    tarefa = _executor.submit(executar)
    # A espera na fila não conta como lentidão do texto: se não houver
    # processador livre, o pedido desiste com 503 em vez de um 504 enganoso.
    if not comecou.wait(timeout=TEMPO_FILA_SEGUNDOS):
        tarefa.cancel()
        raise HTTPException(
            status_code=503,
            detail=(
                "Os modelos estão ocupados com outros textos. "
                "Tente de novo em alguns instantes."
            ),
        )

    inicio = time.perf_counter()
    try:
        saida = tarefa.result(timeout=TEMPO_LIMITE_SEGUNDOS)
    except TempoEsgotado as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                f"O processamento passou de {TEMPO_LIMITE_SEGUNDOS} s e foi "
                "abandonado. Tente um texto menor."
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"O modelo foi carregado, mas falhou ao processar o texto: {exc}",
        ) from exc

    return {
        "tipo_analise": pedido.tipo_analise,
        "modelo": modelo,
        "tempo_segundos": round(time.perf_counter() - inicio, 2),
        **saida,
    }
