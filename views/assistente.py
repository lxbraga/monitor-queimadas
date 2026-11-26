import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import analise  # noqa: E402
import app_utils as u  # noqa: E402
import assistente as a  # noqa: E402

SUGESTOES = [
    "Qual estado teve mais focos?",
    "Qual bioma tem mais focos?",
    "Qual o risco de fogo no Tocantins?",
]


@st.cache_resource(show_spinner="Carregando o modelo de linguagem (o primeiro uso baixa 3 GB)...")
def load_gerador() -> a.Gerador:
    return a.Gerador()


def nova_conversa():
    st.session_state.conversa = a.Memoria()
    st.session_state.mensagens = []


if "conversa" not in st.session_state:
    nova_conversa()

st.title("💬 Assistente")
focos = u.da_referencia(u.focos_ou_aviso())
if focos.empty:
    st.warning("Os dias carregados não têm focos do satélite de referência. Atualize os dados.")
    st.stop()
st.caption(
    f"Pergunte sobre os focos de {focos['dia'].min():%d/%m/%Y} a {focos['dia'].max():%d/%m/%Y} e "
    "sobre as notícias coletadas. O assistente lembra da conversa: depois de perguntar de um "
    "estado, dá para seguir com \"e o segundo?\". O modelo roda nesta máquina e pode errar; "
    "confira em \"De onde veio\"."
)
st.sidebar.button("Nova conversa", on_click=nova_conversa)
st.sidebar.caption(f"Perguntas nesta conversa: {len(st.session_state.mensagens)}")


def mostrar_origem(m: dict):
    if m["sem_origem"]:
        st.warning(
            "Números que não estão nos dados nem nas notícias: " + ", ".join(m["sem_origem"])
        )
    if m["derivados"]:
        st.caption("Contas feitas pelo modelo, confira: " + ", ".join(m["derivados"]))
    if m["tendencia"]:
        st.warning(
            f"A resposta fala em \"{m['tendencia']}\", mas os dados usados não medem tendência."
        )
    if m["fatos"] or m["trechos"]:
        with st.expander("De onde veio"):
            for fato in m["fatos"]:
                st.markdown(f"- {fato}")
            for link, t in {t["link"]: t for t in m["trechos"]}.items():
                st.markdown(f"- Notícia: [{t['titulo']}]({link}), {t['fonte']}, {t['data']}")


for m in st.session_state.mensagens:
    st.chat_message("user").write(m["pergunta"])
    with st.chat_message("assistant"):
        st.markdown(m["resposta"])
        mostrar_origem(m)

sugerida = None
if not st.session_state.mensagens:
    for texto in SUGESTOES:
        if st.button(texto):
            sugerida = texto

pergunta = st.chat_input("Sua pergunta", max_chars=400) or sugerida
if pergunta:
    memoria = st.session_state.conversa
    st.chat_message("user").write(pergunta)
    with st.chat_message("assistant"):
        assunto, fatos, trechos = analise.reunir(pergunta, focos, u.load_busca(), memoria)
        conversa_recente = memoria.ultimas_respostas()
        if assunto.recusa:
            resposta = a.recusar(assunto.recusa, focos["dia"].min(), focos["dia"].max())
            derivados, sem_origem, tendencia, fatos, trechos = [], [], None, [], []
            st.markdown(resposta)
        else:
            mensagens = a.montar_mensagens(
                pergunta, fatos, trechos, memoria, analise.destaque(assunto, pergunta, focos)
            )
            try:
                resposta = st.write_stream(load_gerador().gerar(mensagens)).strip()
            except Exception as exc:
                st.error(
                    "O modelo não pôde responder. Verifique a internet (só no primeiro uso) e a "
                    f"memória livre (cerca de 7 GB). Detalhe: {exc}"
                )
                st.stop()
            derivados, sem_origem = a.conferir_numeros(
                resposta, "\n".join(m["content"] for m in mensagens), conversa_recente
            )
            tendencia = a.conferir_tendencia(
                resposta, "\n".join(fatos) + a.formatar_noticias(trechos)
            )
    # O que foi recusado não entra na memória, para não desviar a conversa.
    if not assunto.recusa:
        memoria.adicionar(pergunta, resposta)
        memoria.assunto = assunto
        analise.aprender_da_resposta(assunto, pergunta, resposta, focos)
    st.session_state.mensagens.append(
        {"pergunta": pergunta, "resposta": resposta, "fatos": fatos, "trechos": trechos,
         "derivados": derivados, "sem_origem": sem_origem, "tendencia": tendencia}
    )
    st.rerun()
