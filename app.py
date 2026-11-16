"""Monitor de Queimadas. Rodar com: streamlit run app.py"""

import streamlit as st

st.set_page_config(page_title="Monitor de Queimadas", page_icon="🔥", layout="wide")

# Mantém os filtros vivos ao navegar entre páginas. Só chaves dos nossos
# widgets de filtro: fixar chaves internas (formulários, botões, uploader)
# faria o Streamlit rejeitar o widget na recriação.
PREFIXOS_PERSISTENTES = ("filtro_", "api_", "llm_", "qtd_dias")
for chave in list(st.session_state):
    if isinstance(chave, str) and chave.startswith(PREFIXOS_PERSISTENTES):
        st.session_state[chave] = st.session_state[chave]

navegacao = st.navigation(
    [
        st.Page("views/painel.py", title="Painel", icon="🔥", default=True),
        st.Page("views/noticias.py", title="Notícias", icon="📰"),
        st.Page("views/dados.py", title="Dados", icon="📂"),
        st.Page("views/consulta_api.py", title="API", icon="🔌"),
        st.Page("views/sobre.py", title="Sobre", icon="🌱"),
    ]
)
navegacao.run()
