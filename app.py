"""Monitor de Queimadas. Rodar com: streamlit run app.py"""

import streamlit as st

st.set_page_config(page_title="Monitor de Queimadas", page_icon="🔥", layout="wide")

# Valores iniciais dos widgets que devem sobreviver à troca de página. Ficam
# aqui, e não nos widgets, porque o Streamlit avisa quando um widget recebe
# valor padrão e também tem valor definido pela sessão. Chaves internas
# (formulários, botões, uploader) não podem ser fixadas e ficam de fora.
VALORES_INICIAIS = {
    "filtro_dias": [],
    "filtro_estados": [],
    "filtro_biomas": [],
    "filtro_fontes": [],
    "filtro_frp": 0.0,
    "qtd_dias": 3,
    "api_url": "http://localhost:8010",
    "api_estado": "",
    "api_bioma": "",
    "api_limite": 20,
    "api_fonte": "todas",
    "llm_tipo": "sentimento",
    "llm_texto": "",
}
for chave, valor in VALORES_INICIAIS.items():
    st.session_state[chave] = st.session_state.get(chave, valor)

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
