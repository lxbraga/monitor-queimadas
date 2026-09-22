"""Raspa notícias sobre queimadas da Agência Brasil com Beautiful Soup.

Gera data/raw/noticias_queimadas.csv (título, categoria, data, link) e
data/processed/corpus_noticias.txt (texto completo dos artigos).

Uso: python code/data_acquisition/scrape_news.py [paginas]
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://agenciabrasil.ebc.com.br"
TAG_URL = f"{BASE_URL}/tags/queimadas"
HEADERS = {"User-Agent": "monitor-queimadas (projeto academico Infnet)"}
TIMEOUT_SECONDS = 30
PAUSE_SECONDS = 1

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CSV_PATH = DATA_DIR / "raw" / "noticias_queimadas.csv"
CORPUS_PATH = DATA_DIR / "processed" / "corpus_noticias.txt"


def get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def parse_listing(soup: BeautifulSoup) -> list[dict]:
    """Extrai as notícias dos cards de uma página de listagem."""
    noticias = []
    for card in soup.select("div.ultima-noticia"):
        titulo = card.select_one("a.titulo-noticia")
        categoria = card.select_one("a.editoria")
        data = card.select_one("span.data")
        if not titulo or not titulo.get("href"):
            continue
        data_match = re.search(r"\d{2}/\d{2}/\d{4}", data.get_text() if data else "")
        noticias.append(
            {
                "titulo": titulo.get_text(strip=True),
                "categoria": categoria.get_text(strip=True) if categoria else "",
                "data": data_match.group() if data_match else "",
                "link": BASE_URL + titulo["href"],
            }
        )
    return noticias


def extract_article_text(soup: BeautifulSoup) -> str:
    """Extrai o texto de um artigo.

    Prefere o JSON do leitor de voz do site (texto completo e limpo);
    sem ele, junta os parágrafos da página.
    """
    tts = soup.find("script", id="tts-data")
    if tts and tts.string:
        try:
            return json.loads(tts.string)["body"]["text"]
        except (json.JSONDecodeError, KeyError):
            pass
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
    return "\n".join(p for p in paragraphs if len(p) > 60)


def main() -> int:
    paginas = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    noticias: list[dict] = []
    vistos: set[str] = set()
    for pagina in range(paginas):
        url = TAG_URL if pagina == 0 else f"{TAG_URL}?page={pagina}"
        print(f"Listagem: {url}")
        try:
            for noticia in parse_listing(get_soup(url)):
                if noticia["link"] not in vistos:
                    vistos.add(noticia["link"])
                    noticias.append(noticia)
        except requests.RequestException as exc:
            print(f"Falha na listagem: {exc}", file=sys.stderr)
        time.sleep(PAUSE_SECONDS)

    if not noticias:
        print("Nenhuma notícia encontrada.", file=sys.stderr)
        return 1

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["titulo", "categoria", "data", "link"])
        writer.writeheader()
        writer.writerows(noticias)
    print(f"{len(noticias)} notícias salvas em {CSV_PATH}")

    textos = []
    for noticia in noticias:
        print(f"Artigo: {noticia['titulo'][:60]}")
        try:
            texto = extract_article_text(get_soup(noticia["link"]))
        except requests.RequestException as exc:
            print(f"Falha no artigo: {exc}", file=sys.stderr)
            continue
        if texto:
            textos.append(texto)
        time.sleep(PAUSE_SECONDS)

    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text("\n\n".join(textos), encoding="utf-8")
    print(f"Corpus com {len(textos)} artigos salvo em {CORPUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
