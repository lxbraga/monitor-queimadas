"""Leitura dos arquivos de data/, compartilhada pelo app e pela API.

Sem dependência do Streamlit, para a API poder importar. Cada lado aplica
o próprio cache e as colunas extras de que precisa.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_DIR / "raw"
FOCOS_API_CSV = RAW_DIR / "focos_api.csv"

# Satélite que o INPE usa nas comparações. O arquivo diário traz todos, e somar
# os satélites conta o mesmo incêndio várias vezes.
SATELITE_REFERENCIA = "AQUA_M-T"

COLUNAS_INPE = [
    "id", "lat", "lon", "data_hora_gmt", "satelite", "municipio", "estado", "pais",
    "municipio_id", "estado_id", "pais_id", "numero_dias_sem_chuva", "precipitacao",
    "risco_fogo", "bioma", "frp",
]

NOTICIAS_CSV = {
    "Agência Brasil": RAW_DIR / "noticias_queimadas.csv",
    "G1": RAW_DIR / "noticias_g1.csv",
}
CORPUS_TXT = [
    DATA_DIR / "processed" / "corpus_noticias.txt",
    DATA_DIR / "processed" / "corpus_g1.txt",
]
SENTIMENTO_CSV = DATA_DIR / "processed" / "noticias_sentimento.csv"
AVALIACAO_CSV = DATA_DIR / "processed" / "resultado_avaliacao_assistente_teste_revisado.csv"


def arquivos_focos(incluir_api: bool = False) -> list[Path]:
    """CSVs diários do INPE e, se pedido, os focos registrados pela API."""
    arquivos = sorted(RAW_DIR.glob("focos_diario_br_*.csv"))
    if incluir_api and FOCOS_API_CSV.exists():
        arquivos.append(FOCOS_API_CSV)
    return arquivos


def assinatura(arquivos: list[Path]) -> tuple:
    """Muda sempre que algum arquivo é criado, apagado ou alterado."""
    return tuple((str(a), a.stat().st_mtime_ns) for a in arquivos if a.exists())


@lru_cache(maxsize=64)
def _ler_csv(caminho: str, alterado_em: int) -> pd.DataFrame:
    """A data de alteração entra na chave: arquivo que não mudou não é relido."""
    return limpar_focos(pd.read_csv(caminho))


def limpar_focos(df: pd.DataFrame) -> pd.DataFrame:
    """Troca por vazio o -999 que o INPE usa para "sem informação" e tira repetidos."""
    df = df.copy()
    for coluna in ("risco_fogo", "precipitacao", "numero_dias_sem_chuva"):
        if coluna in df.columns:
            df[coluna] = df[coluna].where(df[coluna] >= 0)
    return df.drop_duplicates("id") if "id" in df.columns else df


def ler_focos(arquivos: list[Path]) -> pd.DataFrame:
    if not arquivos:
        return pd.DataFrame(columns=COLUNAS_INPE)
    return pd.concat(
        [_ler_csv(str(a), a.stat().st_mtime_ns) for a in arquivos], ignore_index=True
    )


def ler_noticias() -> pd.DataFrame:
    frames = []
    for fonte, caminho in NOTICIAS_CSV.items():
        if caminho.exists():
            df = pd.read_csv(caminho)
            df["fonte"] = fonte
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def ler_artigos() -> pd.DataFrame:
    """Notícias com o texto completo.

    O corpus guarda um artigo por bloco, na ordem do CSV. Se as quantidades não
    baterem (um artigo falhou na coleta), a fonte fica de fora, para não atribuir
    um texto à notícia errada.
    """
    frames = []
    for (fonte, csv), txt in zip(NOTICIAS_CSV.items(), CORPUS_TXT):
        if not (csv.exists() and txt.exists()):
            continue
        df = pd.read_csv(csv)
        textos = txt.read_text(encoding="utf-8").split("\n\n")
        if len(textos) == len(df):
            frames.append(df.assign(fonte=fonte, texto=textos))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def ler_corpus() -> str:
    return "\n\n".join(
        c.read_text(encoding="utf-8") for c in CORPUS_TXT if c.exists()
    )
