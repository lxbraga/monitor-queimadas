import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import app_utils as u  # noqa: E402

st.title("🔥 Painel de focos de calor")
st.caption("Focos detectados por satélite no Brasil, dados abertos do INPE.")

focos = u.focos_completos()
filtrado = u.filtros_sidebar(focos)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Focos de calor", f"{len(filtrado):,}".replace(",", "."))
col2.metric("Municípios", filtrado["municipio"].nunique())
col3.metric("Estados", filtrado["estado"].nunique())
frp_medio = filtrado["frp"].mean()
col4.metric(
    "FRP médio (MW)",
    f"{frp_medio:.1f}" if pd.notna(frp_medio) else "s/d",
    help=u.AJUDA_FRP + " Aqui, a média dos focos filtrados.",
)

if filtrado.empty:
    st.info("Nenhum foco com os filtros atuais.")
else:
    col_esq, col_dir = st.columns(2)
    with col_esq:
        st.subheader("Focos por estado")
        st.bar_chart(filtrado["estado"].value_counts().head(15), color="#d62728")
    with col_dir:
        st.subheader("Focos por bioma")
        st.bar_chart(filtrado["bioma"].value_counts(), color="#ff7f0e")

    st.subheader("Mapa dos focos")
    pontos = filtrado[["lat", "lon"]].dropna()
    if len(pontos) > 5000:
        pontos = pontos.sample(5000, random_state=1)
        st.caption("Amostra de 5.000 focos para manter o mapa leve.")
    st.map(pontos, size=10, color="#d6272880")
