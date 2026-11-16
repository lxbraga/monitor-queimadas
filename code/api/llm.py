"""Modelos de linguagem locais usados pela API.

Os modelos vêm do HuggingFace e rodam inteiramente na máquina local via
Transformers. O download acontece na primeira chamada e fica em cache
(~/.cache/huggingface); depois disso nada sai para a rede.

Modelos:
- Sentimento: lxyuan/distilbert-base-multilingual-cased-sentiments-student
- Resumo: recogna-nlp/ptt5-base-summ

A justificativa da escolha está em docs/project/charter.md.
"""

from __future__ import annotations

import threading

MODELO_SENTIMENTO = "lxyuan/distilbert-base-multilingual-cased-sentiments-student"
MODELO_RESUMO = "recogna-nlp/ptt5-base-summ"

# Os dois modelos leem no máximo 512 tokens; o que passar disso é descartado.
MAX_TOKENS = 512

# Rótulos do classificador em inglês mapeados para a resposta em português.
ROTULOS = {"positive": "positivo", "neutral": "neutro", "negative": "negativo"}

_modelos: dict[str, object] = {}
# Uma trava por modelo: o download de um não pode travar o uso do outro.
_travas = {"sentimento": threading.Lock(), "resumo": threading.Lock()}


def carregar(tarefa: str):
    """Carrega o modelo da tarefa na primeira chamada e o reusa nas seguintes."""
    modelo = _modelos.get(tarefa)
    if modelo is not None:
        return modelo
    with _travas[tarefa]:
        if tarefa not in _modelos:
            if tarefa == "sentimento":
                from transformers import pipeline

                _modelos[tarefa] = pipeline(
                    "sentiment-analysis", model=MODELO_SENTIMENTO
                )
            else:
                # O Transformers v5 removeu o pipeline de summarization,
                # então o modelo seq2seq é usado direto com generate().
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

                _modelos[tarefa] = (
                    AutoTokenizer.from_pretrained(MODELO_RESUMO),
                    AutoModelForSeq2SeqLM.from_pretrained(MODELO_RESUMO),
                )
        return _modelos[tarefa]


def _contar_tokens(tokenizer, texto: str) -> int:
    return len(tokenizer(texto, verbose=False)["input_ids"])


def analisar_sentimento(texto: str) -> dict:
    classificador = carregar("sentimento")
    tokens = _contar_tokens(classificador.tokenizer, texto)
    resultado = classificador(texto, truncation=True)[0]
    return {
        "resultado": {
            "rotulo": ROTULOS.get(resultado["label"], resultado["label"]),
            "confianca": round(float(resultado["score"]), 4),
        },
        "tokens_entrada": tokens,
        "truncado": tokens > MAX_TOKENS,
    }


def resumir(texto: str) -> dict:
    tokenizer, modelo = carregar("resumo")
    tokens = _contar_tokens(tokenizer, texto)
    entrada = tokenizer(
        texto, truncation=True, max_length=MAX_TOKENS, return_tensors="pt"
    )
    saida = modelo.generate(
        **entrada,
        max_new_tokens=150,
        min_new_tokens=20,
        num_beams=4,
        no_repeat_ngram_size=3,
    )
    return {
        "resultado": {
            "resumo": tokenizer.decode(saida[0], skip_special_tokens=True).strip()
        },
        "tokens_entrada": tokens,
        "truncado": tokens > MAX_TOKENS,
    }
