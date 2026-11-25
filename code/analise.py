"""Fatos calculados sobre os focos e busca nas notícias, para o assistente.

Os números que o assistente cita saem daqui, calculados com pandas; o modelo
de linguagem só os interpreta e redige.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

ESTADOS = [
    "ACRE", "ALAGOAS", "AMAPÁ", "AMAZONAS", "BAHIA", "CEARÁ", "DISTRITO FEDERAL",
    "ESPÍRITO SANTO", "GOIÁS", "MARANHÃO", "MATO GROSSO", "MATO GROSSO DO SUL",
    "MINAS GERAIS", "PARÁ", "PARAÍBA", "PARANÁ", "PERNAMBUCO", "PIAUÍ", "RIO DE JANEIRO",
    "RIO GRANDE DO NORTE", "RIO GRANDE DO SUL", "RONDÔNIA", "RORAIMA", "SANTA CATARINA",
    "SÃO PAULO", "SERGIPE", "TOCANTINS",
]

# Palavras que também são nomes de município e apareceriam em perguntas comuns.
MUNICIPIOS_AMBIGUOS = {"central", "reserva", "uniao", "altos", "barra", "natal", "palmas"}

TERMOS_DADOS = re.compile(
    r"quant|foco|estado|bioma|municipio|cidade|ranking|total|media|frp|intens|risco|"
    r"dia\b|dias\b|chuva|percentual|porcent|compar|maior|menor|mais|menos|situacao|"
    r"prioriz|prioridade|regia"
)
# Sem nenhum destes, sem lugar citado e sem notícia relacionada, é outro assunto.
TERMOS_TEMA = re.compile(
    r"foco|queimad|incendi|fogo|fumaca|frp|bioma|risco de fogo|desmat|seca|chuva|brigad|noticia|"
    r"dados|inpe|satelite|situacao|prioriz|prioridade"
)
COBERTURA_TEMA = 0.6

TERMOS_NOTICIAS = re.compile(
    r"noticia|por que|porque|causa|culpa|crim|pris|pres[oa]s?\b|governo|ministr|ibama|"
    r"policia|stf|saude|hospita|respirat|fumaca|qualidade do ar|combat|brigad|multa|lei|"
    r"indigen|estudo|pesquis|especialista|agro|desmat|emiss|aula|voo|quem|imprensa|"
    r"reportag|aconteceu|medida|plano"
)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def numero(valor: float, casas: int = 0) -> str:
    """Formata no padrão brasileiro: 1.234,5."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def nome_proprio(nome: str) -> str:
    minusculas = {"de", "do", "da", "dos", "das", "e"}
    palavras = nome.lower().split()
    return " ".join(
        p if p in minusculas else "(" + p[1:].capitalize() if p[0] == "(" else p.capitalize()
        for p in palavras
    )


@dataclass
class Assunto:
    """Do que a pergunta trata; passa para a próxima quando ela não diz."""

    estados: list[str] = field(default_factory=list)
    biomas: list[str] = field(default_factory=list)
    municipios: list[str] = field(default_factory=list)
    dados: bool = False
    noticias: bool = False
    fora_do_tema: bool = False
    # Lugares das últimas perguntas, como (coluna, nome), para "qual dos dois?".
    pedido: str = ""
    recentes: list[tuple[str, str]] = field(default_factory=list)

    def itens(self) -> list[tuple[str, str]]:
        return (
            [("estado", n) for n in self.estados]
            + [("bioma", n) for n in self.biomas]
            + [("municipio", n) for n in self.municipios]
        )

    @property
    def lugares(self) -> bool:
        return bool(self.estados or self.biomas or self.municipios)


def _achar(nomes: list[str], texto: str) -> tuple[list[str], str]:
    """Nomes citados no texto. Os mais longos primeiro: "Mato Grosso do Sul" não
    pode contar também como "Mato Grosso"."""
    achados = []
    for nome in sorted(nomes, key=len, reverse=True):
        padrao = re.compile(rf"\b{re.escape(normalizar(nome))}\b")
        if padrao.search(texto):
            achados.append(nome)
            texto = padrao.sub(" ", texto)
    return achados, texto


def identificar(pergunta: str, focos: pd.DataFrame, anterior: Assunto | None = None) -> Assunto:
    texto = normalizar(pergunta)
    # "para" é quase sempre a preposição; o estado vem com acento ou artigo.
    e_o_estado = re.search(r"\bpará\b", pergunta.lower()) or re.search(
        r"\b(no|do|ao|o|estado do) para\b(?! )|\b(no|do|ao|o) para\b(?=[ ]*[?,.;]|$)", texto
    )
    if not e_o_estado:
        texto = re.sub(r"\bpara\b", " ", texto)

    estados, resto = _achar(ESTADOS, texto)
    biomas, resto = _achar(list(focos["bioma"].dropna().unique()), resto)
    candidatos = [
        m
        for m in focos["municipio"].dropna().unique()
        if len(m) >= 5 and normalizar(m) not in MUNICIPIOS_AMBIGUOS
    ]
    municipios, _ = _achar(candidatos, resto)

    assunto = Assunto(
        estados, biomas, municipios,
        dados=bool(TERMOS_DADOS.search(texto)), noticias=bool(TERMOS_NOTICIAS.search(texto)),
    )
    chaves = {"estado": "por estado", "bioma": "por bioma", "municipio": "municípios",
              "cidade": "municípios", "dia ": "por dia", "data": "por dia"}
    assunto.pedido = " ".join(v for k, v in chaves.items() if k in texto)
    if anterior:
        if not assunto.lugares and (anterior.lugares):
            assunto.estados = anterior.estados
            assunto.biomas = anterior.biomas
            assunto.municipios = anterior.municipios
        if not assunto.dados and not assunto.noticias:
            assunto.dados, assunto.noticias = anterior.dados, anterior.noticias
    if not assunto.dados and not assunto.noticias:
        assunto.dados = assunto.noticias = True
    if assunto.lugares and not assunto.noticias:
        assunto.dados = True
    anteriores = anterior.recentes if anterior else []
    assunto.recentes = list(dict.fromkeys(assunto.itens() + anteriores))[:3]
    return assunto


def aprender_da_resposta(assunto: Assunto, pergunta: str, resposta: str, focos: pd.DataFrame):
    """Se a pergunta não citou lugar e a resposta citou um só, o assunto vira ele.

    É o que faz "e qual vem depois?" seguido de "que estado lidera nele?" funcionar.
    """
    if identificar(pergunta, focos).lugares:
        return
    citado = identificar(resposta, focos)
    if len(citado.itens()) == 1:
        assunto.estados, assunto.biomas, assunto.municipios = (
            citado.estados, citado.biomas, citado.municipios
        )
        assunto.recentes = list(dict.fromkeys(citado.itens() + assunto.recentes))[:3]


def _ranking(serie: pd.Series, total: int, limite: int | None = None) -> str:
    contagem = serie.value_counts()
    itens = contagem.head(limite) if limite else contagem
    return "; ".join(
        f"{nome_proprio(str(nome))}, {numero(qtd)} focos ({numero(qtd / total * 100, 1)}%)"
        for nome, qtd in itens.items()
    )


def classe_de_risco(valor: float) -> str:
    """Classes usadas pelo INPE para o índice de risco de fogo."""
    limites = [(0.15, "mínimo"), (0.4, "baixo"), (0.7, "médio"), (0.95, "alto")]
    return next((nome for teto, nome in limites if valor <= teto), "crítico")


def _medidas(df: pd.DataFrame) -> str:
    partes = [f"FRP médio {numero(df['frp'].mean(), 1)} MW, máximo {numero(df['frp'].max(), 1)} MW"]
    risco = df["risco_fogo"].dropna() if "risco_fogo" in df else pd.Series(dtype=float)
    if len(risco):
        partes.append(
            f"risco de fogo médio {numero(risco.mean(), 2)} (de 0 a 1, classe "
            f"{classe_de_risco(risco.mean())})"
        )
    secos = df["numero_dias_sem_chuva"].dropna() if "numero_dias_sem_chuva" in df else risco[:0]
    if len(secos):
        partes.append(f"média de {numero(secos.mean(), 1)} dias sem chuva")
    return "; ".join(partes)


def _por_dia(df: pd.DataFrame) -> str:
    return "; ".join(
        f"{dia:%d/%m/%Y}, {numero(qtd)} focos"
        for dia, qtd in df["dia"].value_counts().sort_index().items()
    )


def _com_uf(df: pd.DataFrame) -> pd.Series:
    """Município com o estado, porque há nomes repetidos em estados diferentes."""
    return df["municipio"].astype(str) + " (" + df["estado"].astype(str) + ")"


def fatos_gerais(focos: pd.DataFrame) -> list[str]:
    total = len(focos)
    if not total:
        return ["Não há focos na base."]
    sem_focos = [e for e in ESTADOS if e not in set(focos["estado"])]
    inicio, fim = focos["dia"].min(), focos["dia"].max()
    return [
        f"Período dos dados: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y} ({focos['dia'].nunique()} dias). "
        "Não há dados de focos de outras datas.",
        f"Total no Brasil: {numero(total)} focos, {_medidas(focos)}.",
        f"Focos por dia: {_por_dia(focos)}.",
        f"Focos por bioma, do maior para o menor: {_ranking(focos['bioma'], total)}.",
        f"Focos por estado, do maior para o menor: {_ranking(focos['estado'], total)}.",
        f"Estados sem nenhum foco no período: {', '.join(map(nome_proprio, sem_focos)) or 'nenhum'}.",
        f"Dez municípios com mais focos: {_ranking(_com_uf(focos), total, 10)}.",
    ]


def fatos_do_lugar(nome: str, coluna: str, focos: pd.DataFrame) -> str:
    df = focos[focos[coluna] == nome]
    if df.empty:
        return f"{nome_proprio(nome)}: nenhum foco no período."
    rotulo = {"estado": "Estado", "bioma": "Bioma", "municipio": "Município"}[coluna]
    partes = [
        f"{rotulo} {nome_proprio(nome)}: {numero(len(df))} focos, "
        f"{numero(len(df) / len(focos) * 100, 1)}% do Brasil. {_medidas(df)}.",
        f"Por dia: {_por_dia(df)}.",
    ]
    if coluna != "bioma":
        partes.append(f"Por bioma: {_ranking(df['bioma'], len(df))}.")
    if coluna != "estado":
        partes.append(f"Por estado: {_ranking(df['estado'], len(df), 5)}.")
    if coluna != "municipio":
        partes.append(f"Municípios com mais focos: {_ranking(_com_uf(df), len(df), 5)}.")
    return " ".join(partes)


def comparacoes(itens: list[tuple[str, str]], focos: pd.DataFrame) -> list[str]:
    """Comparação pronta entre lugares do mesmo tipo: o modelo pequeno erra essa conta."""
    frases = []
    for i, (coluna_a, a) in enumerate(itens):
        for coluna_b, b in itens[i + 1 :]:
            if coluna_a != coluna_b:
                continue
            qtd = {n: int((focos[coluna_a] == n).sum()) for n in (a, b)}
            mais, menos = sorted((a, b), key=lambda n: -qtd[n])
            diferenca = qtd[mais] - qtd[menos]
            relacao = (
                f"{nome_proprio(mais)} teve mais focos que {nome_proprio(menos)}, "
                f"com diferença de {numero(diferenca)}"
                if diferenca
                else f"{nome_proprio(mais)} e {nome_proprio(menos)} empatam"
            )
            frases.append(
                f"Comparação: {relacao} ({numero(qtd[mais])} e {numero(qtd[menos])} focos)."
            )
    return frases


def fatos(assunto: Assunto, focos: pd.DataFrame) -> list[str]:
    linhas = [fatos_do_lugar(nome, coluna, focos) for coluna, nome in assunto.itens()[:3]]
    # O que foi perguntado vem antes: modelos pequenos se apoiam no começo.
    gerais = fatos_gerais(focos)
    pedidos = [p for p in ("por estado", "por bioma", "municípios", "por dia") if p in assunto.pedido]
    gerais.sort(key=lambda linha: not any(p in linha for p in pedidos))
    return linhas + gerais


PERGUNTA_COMPARA = re.compile(r"\bdois\b|\bdeles\b|\bdelas\b|diferenca|entre |compar|quem teve")


def destaque(assunto: Assunto, pergunta: str, focos: pd.DataFrame) -> str:
    """Conta já feita, para ir junto da pergunta quando ela compara lugares."""
    if not PERGUNTA_COMPARA.search(normalizar(pergunta)):
        return ""
    itens = assunto.itens() if len(assunto.itens()) > 1 else assunto.recentes[:2]
    return " ".join(comparacoes(itens, focos))


MESES = {
    m: i for i, m in enumerate(
        "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro "
        "dezembro".split(), 1
    )
}


def da_data(trechos: list[dict], pergunta: str) -> list[dict]:
    """Só os trechos publicados no mês e ano citados na pergunta, se houver algum.

    Só o ano não basta: notícia sobre 2024 costuma ser publicada em 2025.
    """
    texto = normalizar(pergunta)
    ano = re.search(r"\b(20\d\d)\b", texto)
    mes = next((n for m, n in MESES.items() if re.search(rf"\b{m}\b", texto)), None)
    if not (ano and mes):
        return trechos
    fim = f"/{mes:02d}/{ano.group(1)}"
    return [t for t in trechos if t["data"].endswith(fim)] or trechos


VAZIAS = set(
    "a o as os e de do da dos das em no na nos nas um uma para por com que se qual quais quem "
    "como quando onde foi foram sao ser esta estao tem ha ao aos sobre mais me diga fale isso "
    "ele ela quantos quanto noticia noticias dizem diz queimada queimadas".split()
)


def _termos(texto: str) -> list[str]:
    # O corte em 6 letras junta variações simples (incêndio, incêndios, incendiário).
    return [p[:6] for p in re.findall(r"[a-z0-9]{3,}", normalizar(texto)) if p not in VAZIAS]


class BuscaNoticias:
    """BM25 sobre trechos das notícias."""

    TAMANHO = 900

    def __init__(self, artigos: pd.DataFrame):
        self.trechos: list[dict] = []
        for _, a in artigos.iterrows():
            for parte in self._partir(str(a["texto"])):
                self.trechos.append(
                    {"titulo": a["titulo"], "fonte": a["fonte"], "data": str(a["data"]),
                     "link": a["link"], "texto": parte}
                )
        self._contagens = [Counter(_termos(t["titulo"] + " " + t["texto"])) for t in self.trechos]
        self._tamanhos = [sum(c.values()) for c in self._contagens]
        self._media = sum(self._tamanhos) / max(len(self._tamanhos), 1)
        documentos = Counter(termo for c in self._contagens for termo in c)
        n = len(self._contagens)
        datas = pd.to_datetime(
            pd.Series([t["data"] for t in self.trechos], dtype="object"),
            format="%d/%m/%Y", errors="coerce",
        )
        # Até 30% a mais para as notícias mais novas: sem data na pergunta, quem
        # pergunta "o que o governo fez" quer o que é recente.
        self._recencia = (datas.rank(pct=True).fillna(0) * 0.3 + 1).tolist()
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in documentos.items()}

    def _partir(self, texto: str) -> list[str]:
        partes, atual = [], ""
        for frase in re.split(r"(?<=[.!?])\s+|\n", texto):
            if atual and len(atual) + len(frase) > self.TAMANHO:
                partes.append(atual.strip())
                atual = ""
            atual += frase + " "
        return partes + ([atual.strip()] if atual.strip() else [])

    def cobertura(self, consulta: str, trechos: list[dict]) -> float:
        """Quanto da consulta o melhor trecho cobre, de 0 a 1, pesando termos raros.

        Conta cada trecho sozinho: juntos, palavras soltas de notícias diferentes
        fariam qualquer pergunta parecer do tema.
        """
        termos = set(_termos(consulta))
        if not termos or not trechos:
            return 0.0
        raro = max(self._idf.values(), default=1.0)
        peso = {t: self._idf.get(t, raro) for t in termos}
        melhor = 0.0
        for t in trechos:
            presentes = set(_termos(t["titulo"] + " " + t["texto"]))
            melhor = max(melhor, sum(p for termo, p in peso.items() if termo in presentes))
        return melhor / sum(peso.values())

    def buscar(self, consulta: str, limite: int = 3) -> list[dict]:
        termos = _termos(consulta)
        notas = []
        for i, contagem in enumerate(self._contagens):
            nota = 0.0
            for t in set(termos):
                f = contagem.get(t, 0)
                if f:
                    ajuste = 1.2 * (0.25 + 0.75 * self._tamanhos[i] / self._media)
                    nota += self._idf[t] * f * 2.2 / (f + ajuste)
            if nota > 0:
                notas.append((nota * self._recencia[i], i))
        escolhidos, links = [], Counter()
        for _, i in sorted(notas, reverse=True):
            # No máximo dois trechos por notícia, para trazer fontes diferentes.
            if links[self.trechos[i]["link"]] < 2:
                links[self.trechos[i]["link"]] += 1
                escolhidos.append(self.trechos[i])
            if len(escolhidos) == limite:
                break
        return escolhidos


def reunir(
    pergunta: str, focos: pd.DataFrame, busca: BuscaNoticias, memoria
) -> tuple[Assunto, list[str], list[dict]]:
    """Assunto, fatos e trechos de notícias que entram no prompt de uma pergunta."""
    assunto = identificar(pergunta, focos, memoria.assunto)
    consulta = pergunta
    # Pergunta curta ("e qual o segundo?") não diz o que buscar sozinha.
    if memoria.trocas and len(_termos(pergunta)) <= 3:
        consulta = memoria.trocas[-1][0] + " " + pergunta
    trechos = da_data(busca.buscar(consulta, 12), pergunta)[:3]
    texto = normalizar(pergunta)
    proprio = identificar(pergunta, focos)
    # O que sobra sem os lugares e as palavras de dados diz se o assunto é outro:
    # "população" e "restaurante" não estão em notícia nenhuma sobre fogo.
    _, sobra = _achar([nome for _, nome in proprio.itens()], texto)
    sobra = " ".join(p for p in re.findall(r"[a-z]{3,}", sobra) if not TERMOS_DADOS.search(p))
    cobertura = busca.cobertura(sobra, trechos) if _termos(sobra) else 1.0
    continuacao = memoria.trocas and consulta != pergunta and not proprio.lugares
    assunto.fora_do_tema = not (
        TERMOS_TEMA.search(texto) or cobertura >= COBERTURA_TEMA or continuacao
    )
    if not assunto.noticias:
        # Pergunta numérica só leva notícia se tudo o que não é dado de foco
        # ("quanto a AGU cobra dos acusados") está junto em um mesmo trecho.
        outros = " ".join(
            p for p in re.findall(r"[a-z]{3,}", texto) if not TERMOS_DADOS.search(p)
        )
        achou = len(_termos(outros)) >= 2 and busca.cobertura(outros, trechos) == 1
        trechos = trechos if achou else []
    if re.search(r"\bdados\b", texto) and "noticia" not in texto:
        trechos = []
    return assunto, fatos(assunto, focos), trechos
