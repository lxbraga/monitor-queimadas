"""Testes das funções puras do scraper do G1 (não abrem navegador)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code" / "data_acquisition"))

from scrape_news_g1 import data_do_link, url_real  # noqa: E402


def test_data_vem_do_link_da_noticia():
    link = "https://g1.globo.com/pa/santarem-regiao/noticia/2026/10/19/fumaca.ghtml"
    assert data_do_link(link) == "19/10/2026"


def test_link_fora_do_padrao_fica_sem_data():
    assert data_do_link("https://g1.globo.com/busca/?q=queimadas") == ""


def test_url_real_desembrulha_o_redirecionador():
    href = (
        "https://measures.globo.com/v1/click?c=busca&u="
        "https%3A%2F%2Fg1.globo.com%2Fam%2Fnoticia%2F2026%2F10%2F01%2Fx.ghtml"
    )
    assert url_real(href) == "https://g1.globo.com/am/noticia/2026/10/01/x.ghtml"
