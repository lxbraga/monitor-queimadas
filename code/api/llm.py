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

# Rótulos do classificador em inglês mapeados para a resposta em português.
ROTULOS = {"positive": "positivo", "neutral": "neutro", "negative": "negativo"}

_pipelines: dict[str, object] = {}
_trava = threading.Lock()


def _pipeline(tarefa: str):
    """Carrega o modelo na primeira chamada e o reusa nas seguintes."""
    with _trava:
        if tarefa not in _pipelines:
            if tarefa == "sentimento":
                from transformers import pipeline

                _pipelines[tarefa] = pipeline(
                    "sentiment-analysis", model=MODELO_SENTIMENTO
                )
            else:
                # O Transformers v5 removeu o pipeline de summarization,
                # então o modelo seq2seq é usado direto com generate().
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

                _pipelines[tarefa] = (
                    AutoTokenizer.from_pretrained(MODELO_RESUMO),
                    AutoModelForSeq2SeqLM.from_pretrained(MODELO_RESUMO),
                )
        return _pipelines[tarefa]


def analisar_sentimento(texto: str) -> dict:
    resultado = _pipeline("sentimento")(texto, truncation=True)[0]
    return {
        "rotulo": ROTULOS.get(resultado["label"], resultado["label"]),
        "confianca": round(float(resultado["score"]), 4),
    }


def resumir(texto: str) -> dict:
    tokenizer, modelo = _pipeline("resumo")
    entrada = tokenizer(texto, truncation=True, max_length=512, return_tensors="pt")
    saida = modelo.generate(
        **entrada,
        max_new_tokens=150,
        min_new_tokens=20,
        num_beams=4,
        no_repeat_ngram_size=3,
    )
    return {"resumo": tokenizer.decode(saida[0], skip_special_tokens=True).strip()}
