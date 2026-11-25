import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import app_utils as u  # noqa: E402

st.title("📂 Dados")

st.session_state.setdefault("uploads", {})
# Trocar a versão troca a chave do uploader, o que o esvazia; sem isso o
# arquivo continuaria nele e voltaria para a base logo depois de limpar.
st.session_state.setdefault("upload_versao", 0)
st.session_state.setdefault("upload_ultimo_id", None)

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
    "entram nos filtros, gráficos e mapa do Painel junto com a base oficial. "
    "Na visão de referência ficam os do AQUA ou sem satélite informado; os de "
    "outros satélites aparecem em \"Todos\". Enviar de novo um arquivo com o "
    "mesmo nome substitui a versão anterior."
)
CHAVE_UPLOAD = f"upload_csv_{st.session_state.upload_versao}"


def ao_mudar_upload():
    """Remover o arquivo no X também tira os focos dele da base.

    Só o clique dispara esta função; trocar de página esvazia o uploader sem
    chamá-la, e os uploads continuam valendo.
    """
    if st.session_state[CHAVE_UPLOAD] is None:
        st.session_state.uploads.pop(st.session_state.get("upload_ultimo_nome"), None)
        st.session_state.upload_erro = None


arquivo = st.file_uploader(
    "Arquivo CSV", type="csv", key=CHAVE_UPLOAD, on_change=ao_mudar_upload
)
if arquivo is not None and arquivo.file_id != st.session_state.upload_ultimo_id:
    st.session_state.upload_ultimo_id = arquivo.file_id
    st.session_state.upload_ultimo_nome = None
    st.session_state.upload_erro = None
    try:
        df_novo = pd.read_csv(arquivo)
    except Exception:
        st.session_state.upload_erro = "Não consegui ler o arquivo como CSV."
    else:
        df_valido, st.session_state.upload_erro = u.validar_upload(df_novo)
        if df_valido is not None:
            st.session_state.uploads[arquivo.name] = df_valido
            st.session_state.upload_ultimo_nome = arquivo.name
            st.rerun()
if arquivo is not None and st.session_state.get("upload_erro"):
    st.error(st.session_state.upload_erro)
if st.session_state.uploads:
    nomes = ", ".join(st.session_state.uploads)
    st.success(f"Uploads ativos: {nomes}")
    if st.button("Limpar uploads"):
        st.session_state.uploads = {}
        st.session_state.upload_versao += 1
        st.session_state.upload_ultimo_id = None
        st.session_state.upload_erro = None
        st.rerun()

st.subheader("Baixar dados filtrados")
st.download_button(
    "Baixar CSV com os filtros atuais",
    # Função em vez de bytes: o CSV só é gerado quando alguém clica.
    lambda: filtrado.to_csv(index=False).encode("utf-8"),
    file_name="focos_filtrados.csv",
    mime="text/csv",
)
