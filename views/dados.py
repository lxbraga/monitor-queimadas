import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import app_utils as u  # noqa: E402

st.title("📂 Dados")

if "uploads" not in st.session_state:
    st.session_state.uploads = {}

focos = u.focos_completos()
filtrado = u.filtros_sidebar(focos)

st.subheader("Amostra da base de focos")
st.dataframe(filtrado.head(100), width="stretch")
st.caption(
    "Dicionário de dados em docs/project/data_summary.md. "
    f"Base atual: {len(focos)} focos, sendo "
    f"{len(focos) - len(u.load_focos())} vindos de uploads."
)

st.subheader("Enviar CSV complementar")
st.markdown(
    "Aceita CSVs no formato dos arquivos diários do INPE. Os focos enviados "
    "entram nos filtros, gráficos e mapa junto com a base oficial."
)
arquivo = st.file_uploader("Arquivo CSV", type="csv", key="upload_csv")
if arquivo is not None and arquivo.name not in st.session_state.uploads:
    try:
        df_novo = pd.read_csv(arquivo)
    except Exception:
        st.error("Não consegui ler o arquivo como CSV.")
    else:
        faltantes = u.COLUNAS_FOCOS - set(df_novo.columns)
        if faltantes:
            st.error(f"Colunas faltando: {', '.join(sorted(faltantes))}")
        else:
            st.session_state.uploads[arquivo.name] = df_novo
            st.rerun()
if st.session_state.uploads:
    nomes = ", ".join(st.session_state.uploads)
    st.success(f"Uploads ativos: {nomes}")
    if st.button("Limpar uploads"):
        st.session_state.uploads = {}
        st.rerun()

st.subheader("Baixar dados filtrados")
st.download_button(
    "Baixar CSV com os filtros atuais",
    filtrado.to_csv(index=False).encode("utf-8"),
    file_name="focos_filtrados.csv",
    mime="text/csv",
)
