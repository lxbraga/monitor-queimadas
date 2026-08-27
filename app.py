"""Demo do TP1. Rodar com: streamlit run app.py"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "code" / "data_acquisition"))

from fetch_inpe import RAW_DIR, fetch_latest_daily  # noqa: E402

st.set_page_config(page_title="Monitor de Queimadas", page_icon="🔥")

st.title("Monitor de Queimadas")
st.caption("Projeto ESG alinhado aos ODS 13 e 15 da Agenda 2030")

st.header("O problema")
st.markdown(
    """
O INPE detecta dezenas de milhares de focos de calor por dia no Brasil, mas
publica esses dados em arquivos técnicos que pouca gente consegue aproveitar.
Quem precisa agir contra as queimadas, como gestores públicos, ONGs e imprensa,
acaba sem uma visão consolidada e atualizada do problema, e fica difícil
priorizar prevenção, fiscalização e resposta.

Este projeto coleta os focos direto dos dados abertos do INPE e os apresenta
em um painel simples, organizado por estado, município e bioma.
"""
)

st.header("Objetivos")
st.markdown(
    """
1. Reunir os dados oficiais de queimadas em um só lugar, com coleta automática via API.
2. Mostrar rapidamente quais estados, municípios e biomas concentram mais focos.
3. Apoiar decisões de prevenção e resposta com indicadores objetivos.
4. Aproximar o público geral dos dados oficiais.

Público-alvo: gestores ambientais, ONGs, jornalistas, pesquisadores e cidadãos.

Nas próximas etapas esta demo evolui para um dashboard interativo, integrando
APIs, WebScraping e LLMs via engenharia de prompts.
"""
)

st.header("Links úteis")
st.markdown(
    """
- [Programa Queimadas (INPE)](https://terrabrasilis.dpi.inpe.br/queimadas/portal/): fonte oficial dos dados
- [Dados abertos de focos de calor (INPE)](https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/): arquivos consumidos pelo projeto
- [TerraBrasilis (INPE)](https://terrabrasilis.dpi.inpe.br/): desmatamento e alertas
- [Agenda 2030 e os 17 ODS (ONU Brasil)](https://brasil.un.org/pt-br/sdgs)
- [Conecta Brasil](https://conectabrasil.org/home): inspiração de iniciativas sociais
- [Observatório do Terceiro Setor](https://observatorio3setor.org.br/carrossel/lista-conheca-projetos-sociais-de-15-causas-diferentes/): inspiração de iniciativas sociais
"""
)

st.header("Amostra dos dados")
st.markdown(
    "Focos de calor do arquivo diário do INPE, os dados que o projeto vai usar."
)


@st.cache_data(ttl=3600)
def load_data() -> tuple[pd.DataFrame, str]:
    files = sorted(RAW_DIR.glob("focos_diario_br_*.csv"))
    if not files:
        fetch_latest_daily()
        files = sorted(RAW_DIR.glob("focos_diario_br_*.csv"))
    latest = files[-1]
    return pd.read_csv(latest), latest.name


if st.button("Atualizar dados do INPE"):
    with st.spinner("Baixando arquivo mais recente..."):
        try:
            fetch_latest_daily()
            load_data.clear()
        except RuntimeError as exc:
            st.error(f"Falha ao atualizar: {exc}")

try:
    df, filename = load_data()
except RuntimeError as exc:
    st.error(
        f"Sem dados: não há amostra em `data/raw/` e o download falhou. {exc}"
    )
    st.stop()

total = f"{len(df):,}".replace(",", ".")
st.markdown(f"Arquivo `{filename}`, {total} focos registrados.")
st.dataframe(df.head(100))
st.caption(
    "Primeiros 100 registros. Dicionário de dados em docs/project/data_summary.md."
)
