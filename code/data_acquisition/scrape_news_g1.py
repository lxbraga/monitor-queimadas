"""Raspa notícias sobre queimadas da busca do G1 com Selenium.

A busca do G1 carrega os resultados por JavaScript (o HTML inicial vem vazio),
por isso o Selenium é necessário. O texto dos artigos, que são páginas
estáticas, é baixado depois com requests e Beautiful Soup.

Gera data/raw/noticias_g1.csv e data/processed/corpus_g1.txt.

Uso: python code/data_acquisition/scrape_news_g1.py [cliques_em_veja_mais]
"""

from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BUSCA_URL = "https://g1.globo.com/busca/?q=queimadas&order=recent"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
TIMEOUT_SECONDS = 30
PAUSE_SECONDS = 1

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CSV_PATH = DATA_DIR / "raw" / "noticias_g1.csv"
CORPUS_PATH = DATA_DIR / "processed" / "corpus_g1.txt"


def url_real(href: str) -> str:
    """A busca envelopa os links num redirecionador; extrai a URL final."""
    query = parse_qs(urlparse(href).query)
    if "u" in query:
        return unquote(query["u"][0])
    return href


def coletar_cards(cliques: int) -> list[dict]:
    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1280,2000")
    driver = webdriver.Chrome(options=opcoes)
    try:
        driver.get(BUSCA_URL)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.widget--card"))
        )
        for _ in range(cliques):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            botoes = driver.find_elements(
                By.CSS_SELECTOR, ".pagination__load-more, [class*='load-more']"
            ) or driver.find_elements(By.PARTIAL_LINK_TEXT, "Veja mais")
            if not botoes:
                break
            driver.execute_script("arguments[0].click()", botoes[0])
            time.sleep(2)
        html = driver.page_source
    finally:
        driver.quit()

    noticias = []
    vistos: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.select("li.widget--card"):
        titulo = card.select_one(".widget--info__title")
        link = card.select_one("a[href]")
        data = card.select_one(".widget--info__meta")
        if not titulo or not link:
            continue
        url = url_real(link["href"])
        if url.startswith("//"):
            url = "https:" + url
        if (
            "g1.globo.com" not in url
            or "/video/" in url
            or "especial-publicitario" in url
            # A busca também acha as cidades chamadas Queimadas (BA e PB),
            # principalmente apuração de eleições; fora do tema do projeto.
            or "/eleicoes/" in url
            or url in vistos
        ):
            continue
        vistos.add(url)
        data_match = re.search(r"\d{2}/\d{2}/\d{4}", data.get_text() if data else "")
        caminho = urlparse(url).path.strip("/").split("/")
        noticias.append(
            {
                "titulo": titulo.get_text(strip=True),
                "categoria": caminho[0] if caminho else "",
                "data": data_match.group() if data_match else "",
                "link": url,
            }
        )
    return noticias


def extrair_texto(url: str) -> str:
    resposta = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    resposta.raise_for_status()
    soup = BeautifulSoup(resposta.text, "html.parser")
    paragrafos = [
        p.get_text(strip=True) for p in soup.select("p.content-text__container")
    ]
    if not paragrafos:
        paragrafos = [
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 80
        ]
    return "\n".join(paragrafos)


def main() -> int:
    cliques = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    print(f"Abrindo a busca do G1 com Selenium ({cliques} cliques em VEJA MAIS)...")
    noticias = coletar_cards(cliques)
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
            texto = extrair_texto(noticia["link"])
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
