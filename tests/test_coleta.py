"""Testes das funções puras do scraper do G1 (não abrem navegador)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code" / "data_acquisition"))

from scrape_news_g1 import data_do_link, estado_do_link, noticias_do_html  # noqa: E402

SECAO = """
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/pa/noticia/2026/10/19/fumaca.ghtml">Fumaça de queimadas cobre Santarém</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/meio-ambiente/noticia/2026/10/18/onca.ghtml">Onça é vista em reserva</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/am/video/incendio.ghtml">Vídeo mostra incêndio</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/pa/noticia/2026/10/19/fumaca.ghtml">Fumaça de queimadas cobre Santarém</a></div>
"""


FALSOS_POSITIVOS = """
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/mundo/noticia/2026/10/09/panama.ghtml">Panamá fica no Círculo de Fogo do Pacífico</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/mundo/noticia/2026/09/10/vulcao.ghtml">Imagens mostram nuvem de fumaça após erupção de vulcão</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/mundo/noticia/2026/11/09/india.ghtml">Densa camada de fumaça encobre capital da Índia</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/ro/noticia/2022/10/12/br319.ghtml">Garimpeiros protestam após dragas serem incendiadas</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/meio-ambiente/noticia/2026/10/02/europa.ghtml">Europa Ocidental teve verão mais quente da história, com seca e incêndios</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/ap/noticia/2025/10/23/ovos.ghtml">Dupla é indiciada por atear fogo em floresta no Amapá</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/ro/noticia/2024/09/01/bolivia.ghtml">Fumaça de queimadas na Bolívia chega a Rondônia</a></div>
"""


def test_falsos_positivos_ficam_de_fora():
    titulos = [n["titulo"] for n in noticias_do_html(FALSOS_POSITIVOS, set())]
    assert titulos == [
        "Dupla é indiciada por atear fogo em floresta no Amapá",
        "Fumaça de queimadas na Bolívia chega a Rondônia",
    ]


def test_noticia_regional_e_do_brasil_mesmo_citando_outro_pais():
    html = """
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/ro/rondonia/noticia/2024/09/01/fumaca.ghtml">Fumaça de queimadas da Bolívia encobre Porto Velho</a></div>
<div class="feed-post"><a class="feed-post-link" href="https://g1.globo.com/meio-ambiente/noticia/2024/09/01/chile.ghtml">Incêndios florestais no Chile deixam mortos</a></div>
"""
    noticias = noticias_do_html(html, set())
    assert [n["titulo"] for n in noticias] == ["Fumaça de queimadas da Bolívia encobre Porto Velho"]
    assert noticias[0]["estado"] == "RO"


def test_estado_vem_do_inicio_do_endereco():
    assert estado_do_link("https://g1.globo.com/ap/amapa/noticia/2026/10/13/x.ghtml") == "AP"
    assert estado_do_link("https://g1.globo.com/meio-ambiente/noticia/2026/10/13/x.ghtml") == ""


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
