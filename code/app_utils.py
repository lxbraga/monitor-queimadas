"""Funções e dados compartilhados pelas páginas do app."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from wordcloud import WordCloud

BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASE_DIR / "code" / "data_acquisition"))

import analise  # noqa: E402
import base_dados  # noqa: E402
from fetch_inpe import fetch_last_days  # noqa: E402

COLUNAS_FOCOS = {"lat", "lon", "data_hora_gmt", "municipio", "estado", "bioma", "frp"}

AJUDA_FRP = (
    "FRP (Fire Radiative Power) é a energia que o fogo irradia, medida pelo "
    "satélite em megawatts. Quanto maior, mais intenso o fogo."
)

OPCOES_SATELITE = ["Referência (AQUA)", "Todos"]
AJUDA_SATELITE = (
    "O INPE recebe dados de vários satélites, e o mesmo incêndio pode aparecer em "
    "mais de um. Para comparar lugares e datas, usa só o de referência (AQUA), que "
    "passa poucas vezes por dia. Todos mostra cada detecção, com repetições."
)

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


def _com_dia(df: pd.DataFrame) -> pd.DataFrame:
    df["data_hora_gmt"] = pd.to_datetime(df["data_hora_gmt"])
    df["dia"] = df["data_hora_gmt"].dt.date
    return df


@st.cache_data(ttl=3600)
def load_focos() -> pd.DataFrame:
    arquivos = base_dados.arquivos_focos()
    if not arquivos:
        fetch_last_days(1)
        arquivos = base_dados.arquivos_focos()
    return _com_dia(base_dados.ler_focos(arquivos))


def focos_ou_aviso() -> pd.DataFrame:
    """Base oficial; sem dados locais nem download possível, explica e para a página."""
    try:
        return load_focos()
    except RuntimeError as exc:
        st.error(
            "Não há arquivos de focos em data/raw/ e o download do INPE falhou. "
            f"Verifique a internet e recarregue a página. ({exc})"
        )
        st.stop()


@st.cache_data(ttl=3600)
def load_noticias() -> pd.DataFrame:
    df = base_dados.ler_noticias()
    if not df.empty:
        df["ano"] = df["data"].astype(str).str.extract(r"(\d{4})")
    return df


@st.cache_data(ttl=3600)
def load_corpus() -> str:
    return base_dados.ler_corpus()


@st.cache_resource(ttl=3600)
def load_busca() -> analise.BuscaNoticias:
    return analise.BuscaNoticias(base_dados.ler_artigos())


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


def validar_upload(df: pd.DataFrame) -> tuple[pd.DataFrame | None, str | None]:
    """Confere colunas e valores de um CSV enviado.

    Retorna a base pronta para somar à oficial, ou None e a explicação do erro.
    """
    faltantes = COLUNAS_FOCOS - set(df.columns)
    if faltantes:
        return None, f"Colunas faltando: {', '.join(sorted(faltantes))}."
    if df.empty:
        return None, "O arquivo não tem nenhuma linha."

    df = df.copy()
    problemas = []
    for coluna, minimo, maximo in [("lat", -90, 90), ("lon", -180, 180)]:
        valores = pd.to_numeric(df[coluna], errors="coerce")
        ruins = valores.isna() | (valores < minimo) | (valores > maximo)
        if ruins.any():
            problemas.append(f"{ruins.sum()} valor(es) inválido(s) em {coluna}")
        df[coluna] = valores

    # Cada valor é lido no próprio formato (o pandas inferiria um só a partir da
    # primeira linha). dayfirst lê 05/09/2026 como 5 de setembro; a coluna é GMT,
    # então valores com fuso são convertidos para UTC e o fuso é removido.
    datas = pd.to_datetime(
        df["data_hora_gmt"], errors="coerce", format="mixed", dayfirst=True, utc=True
    ).dt.tz_convert(None)
    if datas.isna().any():
        problemas.append(f"{datas.isna().sum()} data(s) inválida(s) em data_hora_gmt")
    df["data_hora_gmt"] = datas

    # FRP pode vir vazio, como nos arquivos do INPE, mas não pode ser texto.
    frp = pd.to_numeric(df["frp"], errors="coerce")
    ruins = frp.isna() & df["frp"].notna()
    if ruins.any():
        problemas.append(f"{ruins.sum()} valor(es) não numérico(s) em frp")
    df["frp"] = frp

    if problemas:
        return None, "Arquivo recusado: " + "; ".join(problemas) + "."

    for coluna in ("municipio", "estado", "bioma"):
        df[coluna] = df[coluna].astype("string")
    if "satelite" not in df.columns:
        df["satelite"] = pd.NA
    df["dia"] = df["data_hora_gmt"].dt.date
    return df, None


def focos_completos() -> pd.DataFrame:
    """Base oficial mais os CSVs enviados por upload na sessão."""
    focos = focos_ou_aviso()
    uploads = st.session_state.get("uploads", {})
    if not uploads:
        return focos
    # A combinação só é refeita quando os uploads ou os arquivos do INPE mudam.
    chave = (
        tuple((nome, id(df)) for nome, df in uploads.items()),
        base_dados.assinatura(base_dados.arquivos_focos()),
        len(focos),
    )
    guardado = st.session_state.get("_focos_com_uploads")
    if guardado is None or guardado[0] != chave:
        guardado = (chave, pd.concat([focos, *uploads.values()], ignore_index=True))
        st.session_state["_focos_com_uploads"] = guardado
    return guardado[1]


def da_referencia(focos: pd.DataFrame) -> pd.DataFrame:
    """Focos do satélite de referência; uploads sem satélite também entram."""
    satelite = focos["satelite"]
    return focos[(satelite == base_dados.SATELITE_REFERENCIA) | satelite.isna()]


def multiselect_persistente(container, rotulo: str, opcoes: list, chave: str):
    """Multiselect que descarta valores salvos que sumiram das opções.

    Os valores sobrevivem à troca de página pela sessão, mas as opções vêm
    dos dados; depois de limpar uploads, um estado ou dia só do upload some.
    """
    salvos = st.session_state.get(chave, [])
    st.session_state[chave] = [v for v in salvos if v in opcoes]
    return container.multiselect(rotulo, opcoes, key=chave)


def filtros_sidebar(focos: pd.DataFrame) -> pd.DataFrame:
    """Desenha os filtros na sidebar e retorna a base filtrada."""
    st.sidebar.header("Filtros")
    escolha = st.sidebar.radio(
        "Satélites", OPCOES_SATELITE, key="filtro_satelite", help=AJUDA_SATELITE
    )
    if escolha == OPCOES_SATELITE[0]:
        focos = da_referencia(focos)
    dias = multiselect_persistente(
        st.sidebar, "Dias", sorted(focos["dia"].unique()), "filtro_dias"
    )
    estados = multiselect_persistente(
        st.sidebar, "Estados", sorted(focos["estado"].dropna().unique()), "filtro_estados"
    )
    biomas = multiselect_persistente(
        st.sidebar, "Biomas", sorted(focos["bioma"].dropna().unique()), "filtro_biomas"
    )
    frp_max = focos["frp"].max()
    frp_max = float(frp_max) if pd.notna(frp_max) and frp_max > 0 else 1.0
    # A base pode encolher (uploads removidos) e deixar o valor salvo acima do máximo.
    st.session_state.filtro_frp = min(st.session_state.get("filtro_frp", 0.0), frp_max)
    frp_min = st.sidebar.slider(
        "FRP mínimo (MW)",
        0.0,
        frp_max,
        key="filtro_frp",
        help=AJUDA_FRP + " Aumente o valor para ver só os focos mais intensos.",
    )

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
