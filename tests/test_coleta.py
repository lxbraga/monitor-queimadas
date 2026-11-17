"""Testes das funções puras do scraper do G1 (não abrem navegador)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code" / "data_acquisition"))

from scrape_news_g1 import data_do_link, noticias_do_html  # noqa: E402

SECAO = """
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/pa/noticia/2026/10/19/fumaca.ghtml">Fumaça de queimadas cobre Santarém</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/meio-ambiente/noticia/2026/10/18/onca.ghtml">Onça é vista em reserva</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/am/video/incendio.ghtml">Vídeo mostra incêndio</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/pa/noticia/2026/10/19/fumaca.ghtml">Fumaça de queimadas cobre Santarém</a></div>
"""


def test_data_vem_do_link_da_noticia():
    link = "https://g1.globo.com/pa/santarem-regiao/noticia/2026/10/19/fumaca.ghtml"
    assert data_do_link(link) == "19/10/2026"


def test_link_fora_do_padrao_fica_sem_data():
    assert data_do_link("https://g1.globo.com/meio-ambiente/") == ""


def test_secao_fica_so_com_noticias_sobre_fogo_sem_video_nem_repeticao():
    noticias = noticias_do_html(SECAO, set())
    assert [n["titulo"] for n in noticias] == ["Fumaça de queimadas cobre Santarém"]
    assert noticias[0]["data"] == "19/10/2026"
    assert noticias[0]["categoria"] == "pa"
