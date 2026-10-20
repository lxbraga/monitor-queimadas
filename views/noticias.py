import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import app_utils as u  # noqa: E402

st.title("📰 Notícias sobre queimadas")
st.caption("Conteúdo raspado da Agência Brasil (Beautiful Soup) e do G1 (Selenium).")

noticias = u.load_noticias()
if noticias.empty:
    st.info(
        "Sem notícias raspadas. Rode os scripts em code/data_acquisition/ "
        "(scrape_news.py e scrape_news_g1.py)."
    )
    st.stop()

fontes = st.multiselect(
    "Fontes", sorted(noticias["fonte"].unique()), key="filtro_fontes"
)
if fontes:
    noticias = noticias[noticias["fonte"].isin(fontes)]

st.subheader("Nuvem de palavras das notícias")
corpus = u.load_corpus()
if corpus:
    st.image(u.gerar_nuvem(corpus), width="stretch")
    st.caption("Gerada com o texto completo dos artigos das duas fontes.")

col_fonte, col_ano = st.columns(2)
with col_fonte:
    st.subheader("Notícias por fonte")
    st.bar_chart(noticias["fonte"].value_counts(), color="#d62728")
with col_ano:
    st.subheader("Notícias por ano")
    por_ano = noticias["ano"].dropna().value_counts().sort_index()
    st.bar_chart(por_ano, color="#ff7f0e")

st.subheader(f"Notícias ({len(noticias)})")
st.dataframe(
    noticias[["fonte", "data", "categoria", "titulo", "link"]],
    column_config={"link": st.column_config.LinkColumn("link")},
    hide_index=True,
    width="stretch",
)
