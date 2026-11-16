import pandas as pd
import requests
import streamlit as st

st.title("🔌 API do projeto")
st.markdown(
    "A aplicação expõe os dados por uma API FastAPI. Suba o servidor em outro "
    "terminal e use esta página para consultar e enviar dados."
)
st.code(".venv/bin/uvicorn code.api.main:app --port 8010", language="bash")

url_base = st.text_input("Endereço da API", key="api_url")


def chamar(metodo: str, rota: str, timeout: float = 30, **kwargs):
    """Chama a API e mostra o erro na tela em vez de quebrar a página."""
    try:
        resposta = requests.request(
            metodo, f"{url_base}{rota}", timeout=timeout, **kwargs
        )
    except requests.Timeout:
        st.error(f"A API não respondeu em {timeout:.0f} s.")
        return None
    except requests.RequestException as exc:
        st.error(f"Não foi possível falar com a API: {exc}")
        return None
    if not resposta.ok:
        try:
            detalhe = resposta.json().get("detail", resposta.text)
        except ValueError:
            detalhe = resposta.text
        st.error(f"HTTP {resposta.status_code}: {detalhe}")
        return None
    return resposta.json()


def api_online() -> bool:
    try:
        return requests.get(f"{url_base}/saude", timeout=3).ok
    except requests.RequestException:
        return False


if not api_online():
    st.warning(
        "API fora do ar. Suba o servidor com o comando acima e recarregue; "
        "a documentação interativa fica em /docs."
    )
    st.stop()

st.success(f"API no ar. Documentação interativa em {url_base}/docs")

st.subheader("Consultar focos (GET /focos)")
col1, col2, col3 = st.columns(3)
estado = col1.text_input("Estado (opcional)", key="api_estado")
bioma = col2.text_input("Bioma (opcional)", key="api_bioma")
limite = col3.number_input("Limite", 1, 1000, key="api_limite")
if st.button("Consultar focos"):
    params = {"limite": int(limite)}
    if estado:
        params["estado"] = estado
    if bioma:
        params["bioma"] = bioma
    corpo = chamar("GET", "/focos", params=params)
    if corpo:
        st.caption(f"{corpo['total_filtrado']} focos atendem ao filtro.")
        st.dataframe(pd.DataFrame(corpo["focos"]), width="stretch")

st.subheader("Consultar notícias (GET /noticias)")
fonte = st.selectbox("Fonte", ["todas", "Agência Brasil", "G1"], key="api_fonte")
if st.button("Consultar notícias"):
    params = {} if fonte == "todas" else {"fonte": fonte}
    corpo = chamar("GET", "/noticias", params=params)
    if corpo:
        st.dataframe(pd.DataFrame(corpo["noticias"]), width="stretch")

st.subheader("Processar texto com o modelo local (POST /processar_texto)")
st.markdown(
    "A API roda modelos de linguagem do HuggingFace na própria máquina. "
    "A primeira chamada de cada análise baixa o modelo e demora mais."
)
tipo_analise = st.radio(
    "Análise", ["sentimento", "resumo"], horizontal=True, key="llm_tipo"
)
texto = st.text_area(
    "Texto em português (mínimo 20 caracteres)",
    height=150,
    key="llm_texto",
    placeholder="Cole aqui um trecho de notícia sobre queimadas...",
)
if st.button("Processar texto"):
    with st.spinner("Processando com o modelo local..."):
        # Folga grande porque a primeira chamada inclui o download do modelo.
        corpo = chamar(
            "POST",
            "/processar_texto",
            timeout=600,
            json={"texto": texto, "tipo_analise": tipo_analise},
        )
    if corpo:
        st.json(corpo["resultado"])
        st.caption(
            f"Modelo {corpo['modelo']}, {corpo['tempo_segundos']} s de "
            f"processamento, {corpo['tokens_entrada']} tokens."
        )
        if corpo["truncado"]:
            st.warning(
                "O texto passou do limite do modelo (512 tokens) e só o começo "
                "foi analisado."
            )

st.subheader("Enviar um foco (POST /focos)")
with st.form("form_foco"):
    col1, col2, col3 = st.columns(3)
    lat = col1.number_input("Latitude", -34.0, 6.0, -10.0, format="%.4f")
    lon = col2.number_input("Longitude", -74.0, -34.0, -55.0, format="%.4f")
    frp = col3.number_input("FRP (MW)", 0.0, 5000.0, 10.0)
    col4, col5, col6 = st.columns(3)
    estado_novo = col4.text_input("Estado", "PARÁ")
    municipio = col5.text_input("Município", "")
    bioma_novo = col6.text_input("Bioma", "Amazônia")
    enviado = st.form_submit_button("Enviar via POST")
if enviado:
    corpo = chamar(
        "POST",
        "/focos",
        json={
            "lat": lat,
            "lon": lon,
            "frp": frp,
            "estado": estado_novo,
            "municipio": municipio,
            "bioma": bioma_novo,
        },
    )
    if corpo:
        st.success(f"Foco registrado com o id {corpo['foco']['id']}.")
