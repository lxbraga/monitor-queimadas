"""Respeito ao robots.txt dos sites coletados.

O leitor de robots.txt da biblioteca padrão do Python não entende curingas
(uma regra como "Disallow: /busca/*" passaria despercebida), então as regras
são interpretadas aqui, seguindo o padrão dos buscadores (RFC 9309): curingas
* e $, a regra mais específica vale e, no empate, Allow prevalece.
"""

from __future__ import annotations

import re
import time
from urllib.parse import urlparse

import requests

AGENTE = "monitor-queimadas (projeto academico Infnet)"
TIMEOUT_SECONDS = 30


class ColetaNaoPermitida(Exception):
    """O robots.txt do site proíbe o endereço pedido, ou não pôde ser lido."""


def _padrao(caminho: str) -> re.Pattern:
    regex = re.escape(caminho).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.compile(regex)


class Regras:
    """Regras de um robots.txt para o nosso agente."""

    lidas = True

    def __init__(self, texto: str, agente: str = AGENTE):
        grupos: list[tuple[list[str], list[str]]] = []
        agentes: list[str] = []
        linhas: list[str] = []
        ultima_era_agente = False
        for bruta in texto.splitlines():
            linha = bruta.split("#", 1)[0].strip()
            if ":" not in linha:
                continue
            campo, valor = (p.strip() for p in linha.split(":", 1))
            campo = campo.lower()
            if campo == "user-agent":
                if not ultima_era_agente:
                    agentes, linhas = [], []
                    grupos.append((agentes, linhas))
                agentes.append(valor.lower())
                ultima_era_agente = True
            else:
                linhas.append(f"{campo}:{valor}")
                ultima_era_agente = False

        nome = agente.lower().split()[0]
        especificos = [g for g in grupos if any(a != "*" and a in nome for a in g[0])]
        escolhidos = especificos or [g for g in grupos if "*" in g[0]]

        self.regras: list[tuple[bool, str, re.Pattern]] = []
        self.atraso = 0.0
        for _, linhas_grupo in escolhidos:
            for item in linhas_grupo:
                campo, valor = item.split(":", 1)
                if campo in ("allow", "disallow") and valor:
                    self.regras.append((campo == "allow", valor, _padrao(valor)))
                elif campo == "crawl-delay":
                    try:
                        self.atraso = max(self.atraso, float(valor))
                    except ValueError:
                        pass

    def permite(self, url: str) -> bool:
        partes = urlparse(url)
        caminho = (partes.path or "/") + (f"?{partes.query}" if partes.query else "")
        aplicaveis = [
            (len(texto), permitir)
            for permitir, texto, padrao in self.regras
            if padrao.match(caminho)
        ]
        if not aplicaveis:
            return True
        maior = max(tamanho for tamanho, _ in aplicaveis)
        return any(permitir for tamanho, permitir in aplicaveis if tamanho == maior)


class Coletor:
    """Faz requisições respeitando o robots.txt e o intervalo pedido por site."""

    def __init__(self, agente: str = AGENTE):
        self.agente = agente
        self._regras: dict[str, Regras] = {}
        self._ultima: dict[str, float] = {}

    def regras(self, url: str) -> Regras:
        partes = urlparse(url)
        site = f"{partes.scheme}://{partes.netloc}"
        if site not in self._regras:
            regras = self._baixar_regras(site)
            if not regras.lidas:
                # Não guarda: a falha pode ser passageira.
                return regras
            self._regras[site] = regras
        return self._regras[site]

    def _baixar_regras(self, site: str) -> Regras:
        try:
            resposta = requests.get(
                f"{site}/robots.txt",
                headers={"User-Agent": self.agente},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            # Sem conseguir ler as regras, não coleta nada daquele site.
            return self._nao_lidas()
        if resposta.status_code == 200:
            return Regras(resposta.text, self.agente)
        if 400 <= resposta.status_code < 500:
            return Regras("")
        return self._nao_lidas()

    @staticmethod
    def _nao_lidas() -> Regras:
        regras = Regras("User-agent: *\nDisallow: /")
        regras.lidas = False
        return regras

    def permite(self, url: str) -> bool:
        return self.regras(url).permite(url)

    def esperar(self, url: str, pausa_minima: float = 0) -> None:
        """Aguarda o intervalo pedido pelo site desde a última requisição a ele."""
        site = urlparse(url).netloc
        intervalo = max(self.regras(url).atraso, pausa_minima)
        decorrido = time.monotonic() - self._ultima.get(site, float("-inf"))
        if decorrido < intervalo:
            time.sleep(intervalo - decorrido)
        self._ultima[site] = time.monotonic()

    def get(self, url: str, pausa_minima: float = 0, **kwargs) -> requests.Response:
        regras = self.regras(url)
        if not regras.lidas:
            raise ColetaNaoPermitida(
                f"Não foi possível ler o robots.txt de {urlparse(url).netloc}; verifique a conexão"
            )
        if not regras.permite(url):
            raise ColetaNaoPermitida(f"O robots.txt de {urlparse(url).netloc} proíbe {url}")
        self.esperar(url, pausa_minima)
        kwargs.setdefault("timeout", TIMEOUT_SECONDS)
        headers = {"User-Agent": self.agente, **kwargs.pop("headers", {})}
        return requests.get(url, headers=headers, **kwargs)
