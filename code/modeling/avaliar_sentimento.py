"""Compara abordagens de sentimento no conjunto rotulado do projeto.

O conjunto (data/processed/avaliacao_sentimento.csv) tem títulos reais das
notícias raspadas e frases escritas no mesmo estilo, positivas e neutras, com
vocabulário de fogo, que é onde os classificadores mais erram neste domínio.

Avalia os classificadores de sentimento prontos e a abordagem em uso na API
(zero-shot), chamando a mesma função que a rota /processar_texto usa.

Rodar da raiz do projeto:
    python -m code.modeling.avaliar_sentimento
"""

from __future__ import annotations

import sys
import time

import pandas as pd
from transformers import pipeline

from code.api import llm
from code.base_dados import DATA_DIR

CONJUNTO = DATA_DIR / "processed" / "avaliacao_sentimento.csv"
RESULTADO = DATA_DIR / "processed" / "resultado_avaliacao_sentimento.csv"

CLASSIFICADORES = [
    "lxyuan/distilbert-base-multilingual-cased-sentiments-student",
    "cardiffnlp/twitter-xlm-roberta-base-sentiment",
    "pysentimiento/bertweet-pt-sentiment",
    "tabularisai/multilingual-sentiment-analysis",
]
CLASSES = ["negativo", "neutro", "positivo"]


def normalizar_rotulo(rotulo: str) -> str:
    """Traduz os rótulos dos classificadores (negative, NEG, Very Negative...)."""
    rotulo = rotulo.lower()
    for trecho, traducao in (("neg", "negativo"), ("neu", "neutro"), ("pos", "positivo")):
        if trecho in rotulo:
            return traducao
    return rotulo


def f1_macro(real: pd.Series, previsto: pd.Series) -> float:
    notas = []
    for classe in CLASSES:
        vp = ((previsto == classe) & (real == classe)).sum()
        precisao = vp / max((previsto == classe).sum(), 1)
        revocacao = vp / max((real == classe).sum(), 1)
        soma = precisao + revocacao
        notas.append(2 * precisao * revocacao / soma if soma else 0.0)
    return sum(notas) / len(notas)


def prever_com_classificador(modelo: str, textos: list[str]) -> list[str]:
    classificador = pipeline("sentiment-analysis", model=modelo)
    return [normalizar_rotulo(s["label"]) for s in classificador(textos, truncation=True)]


def prever_com_api(textos: list[str]) -> list[str]:
    return [llm.analisar_sentimento(t)["resultado"]["rotulo"] for t in textos]


def medir(nome: str, prever, dados: pd.DataFrame) -> dict:
    inicio = time.perf_counter()
    previsto = pd.Series(prever(dados["texto"].tolist()))
    ms_por_texto = (time.perf_counter() - inicio) * 1000 / len(dados)
    acerto = previsto == dados["rotulo"]
    escritas = dados["origem"] == "frase_escrita"
    return {
        "abordagem": nome,
        "acuracia": round(acerto.mean(), 3),
        "f1_macro": round(f1_macro(dados["rotulo"], previsto), 3),
        "acuracia_titulos_reais": round(acerto[~escritas].mean(), 3),
        "acuracia_frases_escritas": round(acerto[escritas].mean(), 3),
        "acerto_positivos": round(acerto[dados["rotulo"] == "positivo"].mean(), 3),
        "acerto_neutros": round(acerto[dados["rotulo"] == "neutro"].mean(), 3),
        "acerto_negativos": round(acerto[dados["rotulo"] == "negativo"].mean(), 3),
        "ms_por_texto": round(ms_por_texto, 1),
    }


def main() -> int:
    dados = pd.read_csv(CONJUNTO)
    print(f"{len(dados)} textos: {dados['rotulo'].value_counts().to_dict()}")
    abordagens = [
        (f"zero-shot {llm.MODELO_SENTIMENTO} (em uso na API)", prever_com_api)
    ] + [
        (f"classificador {m}", lambda textos, m=m: prever_com_classificador(m, textos))
        for m in CLASSIFICADORES
    ]
    resultados = []
    for nome, prever in abordagens:
        print(f"Avaliando {nome}...", flush=True)
        try:
            resultados.append(medir(nome, prever, dados))
        except Exception as exc:
            print(f"  falhou: {exc}", file=sys.stderr)
    if not resultados:
        return 1
    tabela = pd.DataFrame(resultados).sort_values("f1_macro", ascending=False)
    tabela.to_csv(RESULTADO, index=False)
    print(tabela.to_string(index=False))
    print(f"\nResultado salvo em {RESULTADO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
