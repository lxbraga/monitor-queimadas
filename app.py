"""Monitor de Queimadas. Rodar com: streamlit run app.py"""

import streamlit as st

st.set_page_config(page_title="Monitor de Queimadas", page_icon="🔥", layout="wide")

# Mantém filtros e uploads vivos ao navegar entre páginas.
for chave in list(st.session_state):
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
