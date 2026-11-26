import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import analise  # noqa: E402
import app_utils as u  # noqa: E402
import base_dados  # noqa: E402

VERMELHO, AZUL, CINZA = "#d62728", "#1f77b4", "#a6a6a6"


def grafico_barras(dados, x, y, altura, cor=None, cores=None, ordem="ascending"):
    """Barras sem zoom, para a rolagem da página não mexer no gráfico."""
    barras = alt.Chart(dados).mark_bar(color=VERMELHO)
    if cor:
        # O deslocamento só vale para barras deitadas, lado a lado.
        deitado = {"yOffset": alt.YOffset(f"{cor}:N", sort=list(cores))} if ":N" in y else {}
        barras = barras.encode(
            color=alt.Color(
                f"{cor}:N", title=None,
                scale=alt.Scale(domain=list(cores), range=list(cores.values())),
                legend=alt.Legend(orient="top"),
            ),
            **deitado,
        )
    eixo_y = alt.Y(y, title=None, sort=ordem, axis=alt.Axis(labelLimit=220)) if ":N" in y else alt.Y(y)
    barras = barras.encode(x=x, y=eixo_y, tooltip=list(dados.columns))
    st.altair_chart(barras.properties(height=altura), width="stretch")


st.title("💡 Dos dados aos insights")
st.caption("O caminho dos dados no projeto, com os números da base carregada agora.")

focos = u.focos_ou_aviso()
ref = u.da_referencia(focos)
if ref.empty:
    st.warning("Os dias carregados não têm focos do satélite de referência. Atualize os dados.")
    st.stop()
artigos = base_dados.ler_artigos()

st.subheader("1. Coleta e limpeza")
col1, col2, col3 = st.columns(3)
col1.metric("Detecções coletadas", analise.numero(len(focos)), help="Todos os satélites do INPE.")
col2.metric(
    "Focos na referência",
    analise.numero(len(ref)),
    help="Só o satélite de referência (AQUA), o que o INPE usa para comparar.",
)
col3.metric("Notícias", len(artigos), help="Com texto completo, da Agência Brasil e do G1.")

# Locais de cerca de 1 km, contados uma vez por dia: aproxima quantos fogos diferentes há.
locais = focos.assign(lat=focos["lat"].round(2), lon=focos["lon"].round(2)).drop_duplicates(
    ["lat", "lon", "dia"]
)
recortes = {"Referência (AQUA)": ref, "Todos, cada local uma vez": locais, "Todos": focos}
parte = pd.DataFrame(
    {nome: df["estado"].value_counts(normalize=True) * 100 for nome, df in recortes.items()}
).fillna(0)
st.markdown(
    f"{focos['satelite'].nunique()} satélites enxergam o mesmo fogo várias vezes: as "
    f"{analise.numero(len(focos))} detecções caem para cerca de "
    f"{analise.numero(len(locais))} contando cada local de 1 km uma vez por dia. Para comparar lugares e datas, o INPE usa um "
    "só, o AQUA, por ser uma série estável ao longo dos anos. A escolha pesa no resultado:"
)
st.markdown(
    "\n".join(
        f"- **{nome}:** {analise.nome_proprio(parte[nome].idxmax())} em primeiro, com "
        f"{analise.numero(parte[nome].max(), 1)}%."
        for nome in recortes
    )
)
maiores = parte.sort_values("Referência (AQUA)", ascending=False).head(8).round(1)
maiores.index = [analise.nome_proprio(e) for e in maiores.index]
longo = maiores.rename_axis("Estado").reset_index().melt(
    "Estado", var_name="Base", value_name="% dos focos"
)
grafico_barras(
    longo, alt.X("% dos focos:Q", title="% do total de cada base"), "Estado:N", 400,
    cor="Base", cores=dict(zip(recortes, (VERMELHO, AZUL, CINZA))),
    ordem=list(maiores.index),
)
st.caption(
    "O AQUA passa poucas vezes por dia. Em poucos dias, parte das diferenças entre estados vem do "
    "horário e do trajeto do satélite, não do fogo. Ele é o padrão do projeto por ser o critério "
    "oficial; o Painel mostra também todos os satélites."
)

st.subheader("2. Onde olhar primeiro")
st.markdown(
    "Quantidade de focos, intensidade e risco contam histórias diferentes. A tabela reúne os "
    "três por estado, para decidir onde prevenir e onde combater."
)
grupos = ref.groupby("estado")
tabela = pd.DataFrame(
    {
        "Focos": grupos.size(),
        "% do país": (grupos.size() / len(ref) * 100).round(1),
        "FRP médio (MW)": grupos["frp"].mean().round(1),
        "Risco de fogo": grupos["risco_fogo"].mean().round(2),
        "Dias sem chuva": grupos["numero_dias_sem_chuva"].mean().round(1),
    }
).sort_values("Focos", ascending=False)
tabela.insert(
    4, "Classe de risco",
    [analise.classe_de_risco(r) if pd.notna(r) else "s/d" for r in tabela["Risco de fogo"]],
)
tabela.index = [analise.nome_proprio(e) for e in tabela.index]
st.dataframe(tabela, width="stretch", height=320)
com_risco = int(ref["risco_fogo"].notna().sum())
if com_risco < len(ref):
    st.caption(
        f"O INPE ainda não preencheu o risco de {analise.numero(len(ref) - com_risco)} dos "
        f"{analise.numero(len(ref))} focos; as médias usam os que têm valor."
    )
MINIMO = 30
relevantes = tabela[tabela["Focos"] >= MINIMO]
if not relevantes.empty:
    intenso = relevantes["FRP médio (MW)"].idxmax()
    st.markdown(
        f"- **Volume:** {tabela.index[0]} tem {analise.numero(tabela['% do país'].iloc[0], 1)}% dos focos.\n"
        f"- **Intensidade:** entre os estados com pelo menos 30 focos, {intenso} tem o maior FRP "
        f"médio ({analise.numero(relevantes.loc[intenso, 'FRP médio (MW)'], 1)} MW).\n"
        f"- **Risco crítico:** "
        f"{', '.join(relevantes.index[relevantes['Classe de risco'] == 'crítico']) or 'nenhum'}."
    )

st.subheader("3. O que a IA leu nas notícias")
if not base_dados.SENTIMENTO_CSV.exists():
    st.info("Rode `python -m code.modeling.gerar_sentimento` para classificar as notícias.")
else:
    sent = pd.read_csv(base_dados.SENTIMENTO_CSV)
    sent["ano"] = sent["data"].astype(str).str.extract(r"(\d{4})")[0]
    por_ano = sent.groupby(["ano", "sentimento"]).size().reset_index(name="notícias")
    cores = {"negativo": VERMELHO, "neutro": CINZA, "positivo": AZUL}
    grafico_barras(
        por_ano, alt.X("ano:N", title=None, axis=alt.Axis(labelAngle=0)), "notícias:Q", 260,
        cor="sentimento", cores=cores,
    )
    st.caption(
        "Sentimento do título, por um modelo local (mDeBERTa, zero-shot). Na avaliação ele "
        "acertou 76% e quase nunca responde neutro. As positivas pedem leitura: na conferência à mão da "
        "base entregue, só 7 das 18 eram boas notícias de fato."
    )
    boas = sent[sent["sentimento"] == "positivo"].sort_values("confianca", ascending=False)
    with st.expander(f"Notícias classificadas como positivas ({len(boas)})"):
        st.dataframe(
            boas[["data", "fonte", "titulo", "confianca", "link"]],
            column_config={"link": st.column_config.LinkColumn("link")},
            hide_index=True, width="stretch",
        )

st.subheader("4. O assistente e o quanto confiar nele")
st.markdown(
    "O Assistente conversa sobre estes dados e lembra do que já foi dito. Os números que ele "
    "cita são calculados antes, por código, e conferidos depois."
)
st.page_link("views/assistente.py", label="Conversar com o Assistente", icon="💬")
if base_dados.AVALIACAO_CSV.exists():
    aval = pd.read_csv(base_dados.AVALIACAO_CSV)
    nomes = {
        "completo": "Em uso", "sem_regras": "Sem as regras do prompt",
        "sem_memoria": "Sem memória", "sem_material": "Sem os dados do projeto",
    }
    certas = aval.groupby("variante")["acertou_revisado"].sum().rename(index=nomes)
    total = aval.groupby("variante").size().iloc[0]
    certas = certas.reindex(nomes.values()).rename_axis("Versão").reset_index(name="certas")
    grafico_barras(
        certas, alt.X("certas:Q", title=f"respostas certas em {total}",
                      scale=alt.Scale(domain=[0, int(total)])),
        "Versão:N", 180, ordem=list(nomes.values()),
    )
    st.caption(
        f"{total} perguntas com resposta conhecida, escritas antes das correções e conferidas à "
        "mão. Os dados e a memória são o que mais pesa. Amostra pequena: diferenças de poucas "
        "perguntas não são conclusivas."
    )

st.subheader("5. O que isso significa para os ODS")
biomas = ref.groupby("bioma").agg(focos=("bioma", "size"), risco=("risco_fogo", "mean"))
biomas = biomas[biomas["focos"] >= MINIMO]
criticos = [e for e in tabela.index if tabela.loc[e, "Classe de risco"] == "crítico"]
linhas = [
    f"- **ODS 15, metas 15.1 e 15.2 (vegetação nativa):** "
    + "; ".join(
        f"{b} tem {analise.numero(n / len(ref) * 100, 1)}% dos focos, com risco "
        f"{analise.classe_de_risco(r) if pd.notna(r) else 's/d'}"
        for b, n, r in biomas.sort_values("focos", ascending=False).head(3).itertuples()
    )
    + ". É onde conservar e prevenir pesa mais.",
]
if criticos:
    linhas.append(
        f"- **ODS 13, meta 13.1 (resiliência a riscos do clima):** {len(criticos)} estados "
        f"estão com risco de fogo crítico ({', '.join(criticos)}), alguns ainda com poucos "
        "focos: são candidatos a prevenção antes que o fogo cresça."
    )
linhas.append(
    "- **ODS 13, meta 13.3 (conscientização):** o dado técnico do INPE vira resposta em "
    "português no Assistente, com a fonte de cada número à vista."
)
st.markdown("\n".join(linhas))
st.caption(
    "O painel não mede impacto: ele organiza a informação para quem decide. São três dias de "
    "dados, sem medir tendência."
)
