"""Raspa notícias sobre queimadas das seções de meio ambiente do G1 com Selenium.

As seções carregam mais notícias por JavaScript, a cada clique em "Mostrar mais",
por isso o Selenium é necessário. A busca do G1 seria mais direta, mas o
robots.txt do site proíbe robôs nela (Disallow: /busca/*), e as seções são
permitidas. Como as seções cobrem vários assuntos, só ficam os títulos sobre
fogo. O texto dos artigos, páginas estáticas, vem depois com requests e
Beautiful Soup.

Gera data/raw/noticias_g1.csv e data/processed/corpus_g1.txt.

Uso: python code/data_acquisition/scrape_news_g1.py [cliques_em_mostrar_mais]
"""

from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from robots import ColetaNaoPermitida, Coletor

SECOES = [
    "https://g1.globo.com/meio-ambiente/",
    "https://g1.globo.com/meio-ambiente/amazonia/",
]
# "Fumaça" sozinha não entra: aparecia em vulcões e poluição urbana, e as
# notícias de fumaça de queimadas já trazem "queimadas" ou "incêndio".
TEMA = re.compile(r"queimad|incêndi|incendi|fogo|focos de calor|brigadist|chamas", re.I)
# Usos de fogo que não são queimada (dragas de garimpo são queimadas em operações).
FORA_DO_TEMA = re.compile(
    r"círculo de fogo|arma de fogo|fogos de artifício|fogo cruzado|vulc|draga", re.I
)
# Notícias regionais do G1 têm a sigla do estado no início do endereço
# (g1.globo.com/ap/...): são do Brasil, e o estado vai para a coluna estado.
ESTADOS = {
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms", "mt", "pa",
    "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to",
}
# Nas seções nacionais não há marcação de lugar, então vale o título: sai a
# notícia que cita outro país ou região sem citar o Brasil, para não perder
# casos como "fumaça da Bolívia chega a Rondônia".
EXTERIOR = re.compile(
    r"europ|portugal|espanha|grécia|frança|itália|turquia|estados unidos|\beua\b|"
    r"califórnia|havaí|canadá|austrália|chile|bolívia|argentina|paraguai|índia|"
    r"indonésia|rússia|sibéria|áfrica|ásia",
    re.I,
)
BRASIL = re.compile(
    r"brasil|amazôni|amazonas|cerrado|pantanal|caatinga|mata atlântica|pampa|"
    r"\bacre\b|alagoas|amapá|bahia|ceará|distrito federal|espírito santo|goiás|"
    r"maranhão|mato grosso|minas gerais|\bpará\b|paraíba|paraná|pernambuco|piauí|"
    r"rio de janeiro|rio grande|rondônia|roraima|santa catarina|são paulo|sergipe|"
    r"tocantins",
    re.I,
)
PAUSE_SECONDS = 1

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CSV_PATH = DATA_DIR / "raw" / "noticias_g1.csv"
CORPUS_PATH = DATA_DIR / "processed" / "corpus_g1.txt"

coletor = Coletor()


def data_do_link(url: str) -> str:
    """Data de publicação (dd/mm/aaaa) tirada do endereço da notícia.

    Os links do G1 seguem o padrão .../noticia/AAAA/MM/DD/...; as seções
    mostram datas relativas ("há 3 dias"), então o link é a fonte confiável.
    """
    achado = re.search(r"/noticia/(\d{4})/(\d{2})/(\d{2})/", url)
    if not achado:
        return ""
    ano, mes, dia = achado.groups()
    return f"{dia}/{mes}/{ano}"


def html_da_secao(driver, url: str, cliques: int) -> str:
    driver.get(url)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.feed-post"))
    )
    for _ in range(cliques):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(PAUSE_SECONDS)
        botoes = driver.find_elements(By.CSS_SELECTOR, "button.load-more")
        if not botoes:
            break
        driver.execute_script("arguments[0].click()", botoes[0])
        time.sleep(2)
    return driver.page_source


def estado_do_link(url: str) -> str:
    """Sigla do estado de uma notícia regional, ou vazio se for nacional."""
    caminho = urlparse(url).path.strip("/").split("/")
    return caminho[0].upper() if caminho and caminho[0] in ESTADOS else ""


def e_do_brasil(titulo: str, url: str) -> bool:
    if estado_do_link(url):
        return True
    return not EXTERIOR.search(titulo) or bool(BRASIL.search(titulo))


def noticias_do_html(html: str, vistos: set[str]) -> list[dict]:
    noticias = []
    for link in BeautifulSoup(html, "html.parser").select("div.feed-post a.feed-post-link"):
        url, titulo = link["href"], link.get_text(strip=True)
        if (
            not TEMA.search(titulo)
            or FORA_DO_TEMA.search(titulo)
            or not e_do_brasil(titulo, url)
            or "/video/" in url
            or "especial-publicitario" in url
            or url in vistos
        ):
            continue
        vistos.add(url)
        caminho = urlparse(url).path.strip("/").split("/")
        noticias.append(
            {
                "titulo": titulo,
                "categoria": caminho[0] if caminho else "",
                "data": data_do_link(url),
                "estado": estado_do_link(url),
                "link": url,
            }
        )
    return noticias


def coletar_cards(cliques: int) -> list[dict]:
    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1280,2000")
    opcoes.add_argument(f"--user-agent={coletor.agente}")
    noticias: list[dict] = []
    vistos: set[str] = set()
    driver = webdriver.Chrome(options=opcoes)
    try:
        for secao in SECOES:
            if not coletor.permite(secao):
                print(f"robots.txt proíbe {secao}; seção ignorada.", file=sys.stderr)
                continue
            print(f"Seção: {secao}")
            noticias += noticias_do_html(html_da_secao(driver, secao, cliques), vistos)
    finally:
        driver.quit()
    return noticias


def extrair_texto(url: str) -> str:
    resposta = coletor.get(url, pausa_minima=PAUSE_SECONDS)
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
    cliques = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    print(f"Abrindo as seções do G1 com Selenium ({cliques} cliques em Mostrar mais)...")
    noticias = coletar_cards(cliques)
    if not noticias:
        print("Nenhuma notícia sobre fogo encontrada.", file=sys.stderr)
        return 1

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["titulo", "categoria", "data", "estado", "link"])
        writer.writeheader()
        writer.writerows(noticias)
    print(f"{len(noticias)} notícias salvas em {CSV_PATH}")

    textos = []
    for noticia in noticias:
        print(f"Artigo: {noticia['titulo'][:60]}")
        try:
            texto = extrair_texto(noticia["link"])
        except (ColetaNaoPermitida, requests.RequestException) as exc:
            print(f"Falha no artigo: {exc}", file=sys.stderr)
            continue
        if texto:
            textos.append(texto)

    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text("\n\n".join(textos), encoding="utf-8")
    print(f"Corpus com {len(textos)} artigos salvo em {CORPUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
