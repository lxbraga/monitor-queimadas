"""Testes do respeito ao robots.txt (sem acesso à rede)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code" / "data_acquisition"))

import robots  # noqa: E402

ROBOTS_G1 = """User-Agent: *
Disallow: /jornalismo/g1/
Disallow: /busca/*
Disallow: /teste-*.html$
"""

ROBOTS_AGENCIA_BRASIL = """User-agent: *
Crawl-delay: 10
Allow: /misc/*.css$
Disallow: /misc/
Disallow: /search/
"""


def test_busca_do_g1_e_proibida():
    regras = robots.Regras(ROBOTS_G1)
    assert not regras.permite("https://g1.globo.com/busca/?q=queimadas&order=recent")


def test_secoes_e_noticias_do_g1_sao_permitidas():
    regras = robots.Regras(ROBOTS_G1)
    assert regras.permite("https://g1.globo.com/meio-ambiente/")
    assert regras.permite("https://g1.globo.com/pa/noticia/2026/10/19/fumaca.ghtml")


def test_cifrao_marca_o_fim_do_endereco():
    regras = robots.Regras(ROBOTS_G1)
    assert not regras.permite("https://g1.globo.com/teste-01.html")
    assert regras.permite("https://g1.globo.com/teste-01.html?x=1")


def test_crawl_delay_da_agencia_brasil_e_lido():
    regras = robots.Regras(ROBOTS_AGENCIA_BRASIL)
    assert regras.atraso == 10
    assert regras.permite("https://agenciabrasil.ebc.com.br/tags/queimadas?page=2")
    assert not regras.permite("https://agenciabrasil.ebc.com.br/search/fogo")


def test_regra_mais_especifica_vale():
    regras = robots.Regras(ROBOTS_AGENCIA_BRASIL)
    assert regras.permite("https://agenciabrasil.ebc.com.br/misc/estilo.css")
    assert not regras.permite("https://agenciabrasil.ebc.com.br/misc/script.php")


def test_grupo_do_proprio_agente_tem_prioridade():
    texto = "User-agent: *\nDisallow: /\n\nUser-agent: monitor-queimadas\nAllow: /\n"
    assert robots.Regras(texto).permite("https://exemplo.com/qualquer")


class RespostaFalsa:
    def __init__(self, status, texto=""):
        self.status_code = status
        self.text = texto


@pytest.mark.parametrize(
    "status, permitido", [(404, True), (403, True), (500, False), (503, False)]
)
def test_status_do_robots_define_a_postura(monkeypatch, status, permitido):
    monkeypatch.setattr(robots.requests, "get", lambda *a, **k: RespostaFalsa(status))
    assert robots.Coletor().permite("https://exemplo.com/pagina") is permitido


def test_coletor_recusa_endereco_proibido(monkeypatch):
    monkeypatch.setattr(robots.requests, "get", lambda *a, **k: RespostaFalsa(200, ROBOTS_G1))
    with pytest.raises(robots.ColetaNaoPermitida):
        robots.Coletor().get("https://g1.globo.com/busca/?q=queimadas")


def test_coletor_respeita_o_intervalo_do_site(monkeypatch):
    monkeypatch.setattr(
        robots.requests, "get", lambda *a, **k: RespostaFalsa(200, "User-agent: *\nCrawl-delay: 5\n")
    )
    esperas = []
    monkeypatch.setattr(robots.time, "sleep", esperas.append)
    coletor = robots.Coletor()
    coletor.esperar("https://exemplo.com/a")
    coletor.esperar("https://exemplo.com/b")
    assert len(esperas) == 1 and 4.9 < esperas[0] <= 5


def test_falha_ao_ler_as_regras_e_explicada_e_nao_fica_guardada(monkeypatch):
    def sem_rede(*a, **k):
        raise robots.requests.ConnectionError

    monkeypatch.setattr(robots.requests, "get", sem_rede)
    coletor = robots.Coletor()
    with pytest.raises(robots.ColetaNaoPermitida, match="Não foi possível ler"):
        coletor.get("https://exemplo.com/pagina")
    monkeypatch.setattr(robots.requests, "get", lambda *a, **k: RespostaFalsa(200, ""))
    assert coletor.permite("https://exemplo.com/pagina")
