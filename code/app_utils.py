"""Funções e dados compartilhados pelas páginas do app."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from wordcloud import WordCloud

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

sys.path.insert(0, str(BASE_DIR / "code" / "data_acquisition"))

from fetch_inpe import RAW_DIR, fetch_last_days  # noqa: E402

NEWS_AB = DATA_DIR / "raw" / "noticias_queimadas.csv"
NEWS_G1 = DATA_DIR / "raw" / "noticias_g1.csv"
CORPUS_AB = DATA_DIR / "processed" / "corpus_noticias.txt"
CORPUS_G1 = DATA_DIR / "processed" / "corpus_g1.txt"

COLUNAS_FOCOS = {"lat", "lon", "data_hora_gmt", "municipio", "estado", "bioma", "frp"}

STOPWORDS_PT = set(
    """a o os as e é de do da dos das em no na nos nas um uma uns umas para por com sem
    sob sobre entre até após ante desde contra que se não mais menos muito muita
    muitos muitas pouco pouca ser está estão foi foram era eram ao aos à às pelo
    pela pelos pelas como quando onde quem qual quais cujo cuja isso isto aquilo
    ele ela eles elas nós vós você vocês seu sua seus suas meu minha nosso nossa
    este esta estes estas esse essa esses essas neste nesta nesse nessa também
    já ainda só apenas ou nem mas porém então assim porque pois há ter tem têm
    tinha ser sendo sido são der dia dias ano anos vai vão ida fazer feito segundo
    segunda afirmou disse informou explicou destacou contou além durante""".split()
)


@st.cache_data(ttl=3600)
def load_focos() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("focos_diario_br_*.csv"))
    if not files:
        fetch_last_days(1)
        files = sorted(RAW_DIR.glob("focos_diario_br_*.csv"))
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df["data_hora_gmt"] = pd.to_datetime(df["data_hora_gmt"])
    df["dia"] = df["data_hora_gmt"].dt.date
    return df


@st.cache_data(ttl=3600)
def load_noticias() -> pd.DataFrame:
    frames = []
    for caminho, fonte in [(NEWS_AB, "Agência Brasil"), (NEWS_G1, "G1")]:
        if caminho.exists():
            df = pd.read_csv(caminho)
            df["fonte"] = fonte
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["ano"] = df["data"].astype(str).str.extract(r"(\d{4})")
    return df


@st.cache_data(ttl=3600)
def load_corpus() -> str:
    partes = [
        p.read_text(encoding="utf-8") for p in (CORPUS_AB, CORPUS_G1) if p.exists()
    ]
    return "\n\n".join(partes)


@st.cache_data
def gerar_nuvem(texto: str):
    nuvem = WordCloud(
        width=900,
        height=400,
        background_color="white",
        stopwords=STOPWORDS_PT,
        colormap="Reds",
        collocations=False,
    ).generate(texto.lower())
    return nuvem.to_array()


def focos_completos() -> pd.DataFrame:
    """Base oficial mais os CSVs enviados por upload na sessão."""
    focos = load_focos()
    uploads = st.session_state.get("uploads", {})
    if uploads:
        extras = pd.concat(uploads.values(), ignore_index=True)
        extras["data_hora_gmt"] = pd.to_datetime(extras["data_hora_gmt"])
        extras["dia"] = extras["data_hora_gmt"].dt.date
        focos = pd.concat([focos, extras], ignore_index=True)
    return focos


def filtros_sidebar(focos: pd.DataFrame) -> pd.DataFrame:
    """Desenha os filtros na sidebar e retorna a base filtrada."""
    st.sidebar.header("Filtros")
    dias = st.sidebar.multiselect(
        "Dias", sorted(focos["dia"].unique()), key="filtro_dias"
    )
    estados = st.sidebar.multiselect(
        "Estados", sorted(focos["estado"].dropna().unique()), key="filtro_estados"
    )
    biomas = st.sidebar.multiselect(
        "Biomas", sorted(focos["bioma"].dropna().unique()), key="filtro_biomas"
    )
    frp_max = focos["frp"].max()
    frp_max = float(frp_max) if pd.notna(frp_max) and frp_max > 0 else 1.0
    # A base pode encolher (uploads removidos) e deixar o valor salvo acima do máximo.
    st.session_state.filtro_frp = min(st.session_state.get("filtro_frp", 0.0), frp_max)
    frp_min = st.sidebar.slider("FRP mínimo (MW)", 0.0, frp_max, key="filtro_frp")

    st.sidebar.divider()
    qtd_dias = st.sidebar.number_input("Dias a baixar", 1, 14, key="qtd_dias")
    if st.sidebar.button("Atualizar dados do INPE"):
        with st.spinner("Baixando arquivos do INPE..."):
            try:
                fetch_last_days(int(qtd_dias))
                load_focos.clear()
                st.rerun()
            except RuntimeError as exc:
                st.sidebar.error(f"Falha ao atualizar: {exc}")

    filtrado = focos
    if dias:
        filtrado = filtrado[filtrado["dia"].isin(dias)]
    if estados:
        filtrado = filtrado[filtrado["estado"].isin(estados)]
    if biomas:
        filtrado = filtrado[filtrado["bioma"].isin(biomas)]
    if frp_min > 0:
        filtrado = filtrado[filtrado["frp"] >= frp_min]
    return filtrado
