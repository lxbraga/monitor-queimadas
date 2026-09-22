"""Monitor de Queimadas. Rodar com: streamlit run app.py"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from wordcloud import WordCloud

sys.path.insert(0, str(Path(__file__).resolve().parent / "code" / "data_acquisition"))

from fetch_inpe import RAW_DIR, fetch_last_days  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "data"
NEWS_CSV = DATA_DIR / "raw" / "noticias_queimadas.csv"
CORPUS_TXT = DATA_DIR / "processed" / "corpus_noticias.txt"

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

st.set_page_config(page_title="Monitor de Queimadas", page_icon="🔥", layout="wide")


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
    if not NEWS_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(NEWS_CSV)
    df["ano"] = df["data"].str.slice(6, 10)
    return df


@st.cache_data(ttl=3600)
def load_corpus() -> str:
    return CORPUS_TXT.read_text(encoding="utf-8") if CORPUS_TXT.exists() else ""


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


st.title("🔥 Monitor de Queimadas")
st.caption("Focos de calor no Brasil com dados do INPE. ODS 13 e 15 da Agenda 2030.")

with st.expander("Sobre o projeto"):
    st.markdown(
        """
O INPE detecta dezenas de milhares de focos de calor por dia no Brasil, mas
publica esses dados em arquivos técnicos que pouca gente consegue aproveitar.
Este painel reúne os focos e as notícias sobre o tema em um só lugar, para
apoiar gestores públicos, ONGs, imprensa, pesquisadores e cidadãos.

Links úteis:
[Programa Queimadas (INPE)](https://terrabrasilis.dpi.inpe.br/queimadas/portal/),
[dados abertos de focos](https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/),
[Agência Brasil](https://agenciabrasil.ebc.com.br/tags/queimadas),
[Agenda 2030 (ONU Brasil)](https://brasil.un.org/pt-br/sdgs),
[Conecta Brasil](https://conectabrasil.org/home),
[Observatório do Terceiro Setor](https://observatorio3setor.org.br/carrossel/lista-conheca-projetos-sociais-de-15-causas-diferentes/).
"""
    )

if "uploads" not in st.session_state:
    st.session_state.uploads = {}

focos = load_focos()
if st.session_state.uploads:
    extras = pd.concat(st.session_state.uploads.values(), ignore_index=True)
    extras["data_hora_gmt"] = pd.to_datetime(extras["data_hora_gmt"])
    extras["dia"] = extras["data_hora_gmt"].dt.date
    focos = pd.concat([focos, extras], ignore_index=True)

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
frp_min = st.sidebar.slider(
    "FRP mínimo (MW)", 0.0, float(focos["frp"].max() or 1), 0.0, key="filtro_frp"
)

st.sidebar.divider()
qtd_dias = st.sidebar.number_input("Dias a baixar", 1, 14, 3, key="qtd_dias")
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

aba_painel, aba_noticias, aba_dados = st.tabs(["Painel", "Notícias", "Dados"])

with aba_painel:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Focos de calor", f"{len(filtrado):,}".replace(",", "."))
    col2.metric("Municípios", filtrado["municipio"].nunique())
    col3.metric("Estados", filtrado["estado"].nunique())
    frp_medio = filtrado["frp"].mean()
    col4.metric("FRP médio (MW)", f"{frp_medio:.1f}" if pd.notna(frp_medio) else "s/d")

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

with aba_noticias:
    noticias = load_noticias()
    if noticias.empty:
        st.info(
            "Sem notícias raspadas. Rode `python code/data_acquisition/scrape_news.py`."
        )
    else:
        st.subheader("Nuvem de palavras das notícias")
        corpus = load_corpus()
        if corpus:
            st.image(gerar_nuvem(corpus), width="stretch")

        col_cat, col_ano = st.columns(2)
        with col_cat:
            st.subheader("Notícias por categoria")
            st.bar_chart(noticias["categoria"].value_counts(), color="#d62728")
        with col_ano:
            st.subheader("Notícias por ano")
            st.bar_chart(noticias["ano"].value_counts().sort_index(), color="#ff7f0e")

        st.subheader(f"Notícias da Agência Brasil ({len(noticias)})")
        st.dataframe(
            noticias[["data", "categoria", "titulo", "link"]],
            column_config={"link": st.column_config.LinkColumn("link")},
            hide_index=True,
            width="stretch",
        )

with aba_dados:
    st.subheader("Amostra da base de focos")
    st.dataframe(filtrado.head(100), width="stretch")
    st.caption(
        "Dicionário de dados em docs/project/data_summary.md. "
        f"Base atual: {len(focos)} focos, sendo "
        f"{len(focos) - len(load_focos())} vindos de uploads."
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
            faltantes = COLUNAS_FOCOS - set(df_novo.columns)
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
