"""Classifica o sentimento do título de cada notícia coletada.

Usa a mesma função da API. Só o título, que é onde o modelo foi avaliado.
Gera data/processed/noticias_sentimento.csv, lido pela página Insights.

Rodar da raiz do projeto, depois de coletar notícias:
    python -m code.modeling.gerar_sentimento
"""

from code import base_dados
from code.api import llm


def main() -> int:
    noticias = base_dados.ler_noticias()
    saidas = [llm.analisar_sentimento(t)["resultado"] for t in noticias["titulo"]]
    noticias["sentimento"] = [s["rotulo"] for s in saidas]
    noticias["confianca"] = [s["confianca"] for s in saidas]
    noticias[["fonte", "data", "titulo", "link", "sentimento", "confianca"]].to_csv(
        base_dados.SENTIMENTO_CSV, index=False
    )
    print(noticias["sentimento"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
