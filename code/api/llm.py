"""Modelos de linguagem locais usados pela API.

Os modelos vêm do HuggingFace e rodam inteiramente na máquina local via
Transformers. O download acontece na primeira chamada e fica em cache
(~/.cache/huggingface); depois disso nada sai para a rede.

Modelos:
- Sentimento: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7,
  usado em classificação zero-shot
- Resumo: recogna-nlp/ptt5-base-summ

A justificativa e a avaliação estão em docs/project/charter.md; a comparação
pode ser refeita com python -m code.modeling.avaliar_sentimento.
"""

from __future__ import annotations

import threading

MODELO_SENTIMENTO = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
MODELO_RESUMO = "recogna-nlp/ptt5-base-summ"

# Os dois modelos leem no máximo 512 tokens; o que passar disso é descartado.
MAX_TOKENS = 512

# Zero-shot: o modelo de inferência julga qual destas frases o texto confirma.
# Hipótese e rótulos foram fixados antes da avaliação, não ajustados a ela.
HIPOTESE_SENTIMENTO = "Esta notícia é {}."
ROTULOS_SENTIMENTO = {"positiva": "positivo", "negativa": "negativo", "neutra": "neutro"}

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
                    "zero-shot-classification", model=MODELO_SENTIMENTO
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
    resultado = classificador(
        texto,
        candidate_labels=list(ROTULOS_SENTIMENTO),
        hypothesis_template=HIPOTESE_SENTIMENTO,
    )
    return {
        "resultado": {
            "rotulo": ROTULOS_SENTIMENTO[resultado["labels"][0]],
            "confianca": round(float(resultado["scores"][0]), 4),
        },
        "tokens_entrada": tokens,
        "truncado": tokens > MAX_TOKENS,
    }


def resumir(texto: str) -> dict:
    import torch

    tokenizer, modelo = carregar("resumo")
    ids = tokenizer(texto, verbose=False)["input_ids"]
    tokens = len(ids)
    if tokens > MAX_TOKENS:
        # O modelo espera o marcador de fim, que o corte deixaria de fora.
        ids = ids[: MAX_TOKENS - 1] + [tokenizer.eos_token_id]
    saida = modelo.generate(
        input_ids=torch.tensor([ids]),
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
