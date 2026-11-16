"""Leitura dos arquivos de data/, compartilhada pelo app e pela API.

Sem dependência do Streamlit, para a API poder importar. Cada lado aplica
o próprio cache e as colunas extras de que precisa.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_DIR / "raw"
FOCOS_API_CSV = RAW_DIR / "focos_api.csv"

NOTICIAS_CSV = {
    "Agência Brasil": RAW_DIR / "noticias_queimadas.csv",
    "G1": RAW_DIR / "noticias_g1.csv",
}
CORPUS_TXT = [
    DATA_DIR / "processed" / "corpus_noticias.txt",
    DATA_DIR / "processed" / "corpus_g1.txt",
]


def arquivos_focos(incluir_api: bool = False) -> list[Path]:
    """CSVs diários do INPE e, se pedido, os focos registrados pela API."""
    arquivos = sorted(RAW_DIR.glob("focos_diario_br_*.csv"))
    if incluir_api and FOCOS_API_CSV.exists():
        arquivos.append(FOCOS_API_CSV)
    return arquivos


def assinatura(arquivos: list[Path]) -> tuple:
    """Muda sempre que algum arquivo é criado, apagado ou alterado."""
    return tuple((str(a), a.stat().st_mtime_ns) for a in arquivos if a.exists())


def ler_focos(arquivos: list[Path]) -> pd.DataFrame:
    if not arquivos:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(a) for a in arquivos], ignore_index=True)


def ler_noticias() -> pd.DataFrame:
    frames = []
    for fonte, caminho in NOTICIAS_CSV.items():
        if caminho.exists():
            df = pd.read_csv(caminho)
            df["fonte"] = fonte
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def ler_corpus() -> str:
    return "\n\n".join(
        c.read_text(encoding="utf-8") for c in CORPUS_TXT if c.exists()
    )
