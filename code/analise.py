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
    r"dia\b|dias\b|chuva|chove|percentual|porcent|compar|maior|menor|mais|menos|situacao|"
    r"prioriz|prioridade|regia"
)
# Sem nenhum destes, sem lugar citado e sem notícia relacionada, é outro assunto.
TERMOS_TEMA = re.compile(
    r"foco|queimad|incendi|fogo|fumaca|frp|bioma|risco de fogo|desmat|seca|chuv|chov|risco|brigad|noticia|"
    r"dados|inpe|satelite|situacao|prioriz|prioridade"
)
COBERTURA_TEMA = 0.6

# Palavras de quem continua a conversa; não dizem se o assunto é outro.
TERMOS_CONVERSA = re.compile(
    r"^(vem|depois|antes|primeir\w*|segund\w*|terceir\w*|ultim\w*|anterior\w*|dois|duas|ambos|"
    r"eles?|elas?|diferenca\w*|deles?|delas?|nele|nela|entre|la|ali|nisso|disso|tambem|pergunt\w*|respond\w*|disse|falou|"
    r"falei|conversa|voltando|lider\w*|afetad\w*|atingid\w*|fica|ficam|concentra\w*|teve|tiveram|"
    r"houve|pior|melhor|entao|mesm[oa]|outr[oa]s?|agora|isso|soma\w*|junt[oa]s|representa|explique|"
    r"resuma|detalh\w*|aparece|lugar|ser|esse|essa|desse|dessa|nesse|nessa|todo|toda|tudo)$"
)

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


ANAFORA = re.compile(
    r"\b(la|ali|nel[ea]|del[ea]s?|el[ea]s?|iss[oa]|ness[ea]|dess[ea]|ess[ea]|dois|ambos)\b"
)


@dataclass
class Assunto:
    """Do que a pergunta trata; passa para a próxima quando ela não diz."""

    estados: list[str] = field(default_factory=list)
    biomas: list[str] = field(default_factory=list)
    municipios: list[str] = field(default_factory=list)
    dados: bool = False
    noticias: bool = False
    # Por que o código responde sem chamar o modelo: "tema", "periodo" ou vazio.
    recusa: str = ""
    # Lugares das últimas perguntas, como (coluna, nome), para "qual dos dois?".
    pedido: str = ""
    texto: str = ""
    # O que está sendo ordenado: estado, bioma, municipio ou dia.
    nivel: str = ""
    posicao: int = 1
    crescente: bool = False
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
    # "E na Bahia?" ainda é sobre o risco, o dia ou o FRP da pergunta anterior.
    continua = anterior and not TERMOS_DADOS.search(texto)
    assunto.texto = f"{texto} {anterior.texto}" if continua else texto
    niveis = {"estado": "estado", "bioma": "bioma", "municipio": "municipio", "cidade": "municipio"}
    assunto.nivel = next((v for k, v in niveis.items() if k in texto), "")
    if not assunto.nivel and re.search(r"\b(que|qual) dia\b", texto):
        assunto.nivel = "dia"
    nivel_citado = assunto.nivel
    if anterior:
        assunto.nivel = assunto.nivel or anterior.nivel
        assunto.posicao, assunto.crescente = anterior.posicao, anterior.crescente
    assunto.pedido = " ".join(v for k, v in chaves.items() if k in texto)
    if anterior:
        # Pergunta completa, sem "lá" nem "dele", não continua o lugar anterior.
        continua = texto.startswith("e ") or ANAFORA.search(texto)
        completa = (
            re.search(r"\b(no|todo o|do) (pais|brasil)\b.*foco|foco.*\b(no|todo o|do) (pais|brasil)\b", texto)
            or nivel_citado in ("estado", "bioma")
            or (nivel_citado == "dia" and "foco" in texto)
            or ("foco" in texto and re.search(r"\d{1,2}/\d{1,2}", texto))
        )
        do_pais = completa and not continua
        if not assunto.lugares and anterior.lugares and not do_pais:
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
    assunto.recentes = list(dict.fromkeys(assunto.itens() + anteriores))[:5]
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
        assunto.recentes = list(dict.fromkeys(citado.itens() + assunto.recentes))[:5]


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


def _risco(valores: pd.Series) -> str:
    # Sem a palavra "médio" junto do índice: o modelo a lia como a classe do risco.
    media = valores.mean()
    return f"classe {classe_de_risco(media).upper()} (índice {numero(media, 2)} de 1)"


def _medidas(df: pd.DataFrame) -> str:
    partes = [f"FRP médio {numero(df['frp'].mean(), 1)} MW, máximo {numero(df['frp'].max(), 1)} MW"]
    risco = df["risco_fogo"].dropna() if "risco_fogo" in df else pd.Series(dtype=float)
    if len(risco):
        partes.append(f"risco de fogo: {_risco(risco)}")
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


def comparacoes(
    itens: list[tuple[str, str]], focos: pd.DataFrame, menos: bool = False
) -> list[str]:
    """Comparação pronta entre lugares do mesmo tipo: o modelo pequeno erra essa conta."""
    frases = []
    for i, (coluna_a, a) in enumerate(itens):
        for coluna_b, b in itens[i + 1 :]:
            if coluna_a != coluna_b:
                continue
            qtd = {n: int((focos[coluna_a] == n).sum()) for n in (a, b)}
            um, outro = sorted((a, b), key=lambda n: qtd[n] if menos else -qtd[n])
            if qtd[um] == qtd[outro]:
                frases.append(
                    f"{nome_proprio(um)} e {nome_proprio(outro)} empatam, com {numero(qtd[um])}."
                )
                continue
            frases.append(
                f"{nome_proprio(um)} teve {'menos' if menos else 'mais'} focos "
                f"({numero(qtd[um])}) que {nome_proprio(outro)} ({numero(qtd[outro])}); "
                f"a diferença é {numero(abs(qtd[um] - qtd[outro]))}."
            )
    return frases


def _estados_por_risco(focos: pd.DataFrame) -> str:
    media = focos.groupby("estado")["risco_fogo"].mean().dropna().sort_values(ascending=False)
    classes: dict[str, list[str]] = {}
    for estado, valor in media.items():
        classes.setdefault(classe_de_risco(valor), []).append(nome_proprio(estado))
    return "Estados por classe de risco de fogo: " + "; ".join(
        f"{classe.upper()}: {', '.join(nomes)}" for classe, nomes in classes.items()
    ) + "."


MINIMO_DE_FOCOS = 30


def _estados_por_frp(focos: pd.DataFrame) -> str:
    grupos = focos.groupby("estado")["frp"].agg(["size", "mean"])
    grupos = grupos[grupos["size"] >= MINIMO_DE_FOCOS].sort_values("mean", ascending=False)
    return (
        f"FRP médio por estado, do maior para o menor (com pelo menos {MINIMO_DE_FOCOS} focos): "
        + "; ".join(f"{nome_proprio(e)}, {numero(m, 1)} MW" for e, m in grupos["mean"].items())
        + "."
    )


def fatos(assunto: Assunto, focos: pd.DataFrame) -> list[str]:
    linhas = [fatos_do_lugar(nome, coluna, focos) for coluna, nome in assunto.itens()[:3]]
    # O que foi perguntado vem antes: modelos pequenos se apoiam no começo.
    gerais = fatos_gerais(focos)
    texto = assunto.texto
    if "risco" in texto or "classe" in texto:
        linhas.append(_estados_por_risco(focos))
    if "frp" in texto or "intens" in texto:
        linhas.append(_estados_por_frp(focos))
    pedidos = [p for p in ("por estado", "por bioma", "municípios", "por dia") if p in assunto.pedido]
    gerais.sort(key=lambda linha: not any(p in linha for p in pedidos))
    return linhas + gerais


PERGUNTA_COMPARA = re.compile(r"\bdois\b|\bdeles\b|\bdelas\b|diferenca|entre |compar|quem teve")


def _dia_citado(texto: str, focos: pd.DataFrame):
    """Dia da base citado na pergunta ("20/09", "dia 20" ou "20 de setembro"), se houver."""
    achado = re.search(r"\b(\d{1,2})/\d{1,2}|\bdia (\d{1,2})\b|\b(\d{1,2}) de [a-z]+", texto)
    if not achado:
        return None
    dia = int(next(g for g in achado.groups() if g))
    return next((d for d in focos["dia"].unique() if d.day == dia), None)


SUPERLATIVO = re.compile(
    r"\bmais\b|\bmaior\b|\bmenos\b|\bmenor\b|lider|primeir|\bsegund[oa]\b(?! [oa]s?\b)|terceir|"
    r"quart[oa]\b|ultim|pior|vem depois|concentra"
)
ORDINAIS = {
    r"\bsegund[oa]\b(?! [oa]s?\b)": 2, r"terceir": 3, r"\bquart[oa]\b": 4, r"quint[oa]\b": 5,
}
MEDIDAS = {
    "frp": ("FRP médio", "MW", 1), "risco_fogo": ("índice de risco de fogo", "", 2),
    "numero_dias_sem_chuva": ("média de dias sem chuva", "dias", 1),
}


def _ordem(assunto: Assunto, pergunta: str, focos: pd.DataFrame) -> str:
    """Quem ocupa a posição que a pergunta pede ("o segundo com menos focos")."""
    if not assunto.nivel or "pergunt" in normalizar(pergunta) or not re.search(r"\b(qual|que|quem|e [oa])\b", normalizar(pergunta)):
        return ""
    # Município de um estado, estado de um bioma: ordena dentro do lugar citado.
    dentro = [(c, n) for c, n in assunto.itens() if c != assunto.nivel]
    df = focos
    for coluna, nome in dentro[:1]:
        df = df[df[coluna] == nome]
    texto = normalizar(pergunta)
    medida = (
        "frp" if re.search(r"frp|intens", texto)
        else "risco_fogo" if "risco" in texto
        else "numero_dias_sem_chuva" if re.search(r"chuva|chove|seco", texto)
        else ""
    )
    grupos = df.groupby("dia" if assunto.nivel == "dia" else assunto.nivel)
    if medida:
        nome_medida, unidade, casas = MEDIDAS[medida]
        media = grupos[medida].mean()
        valores = media[grupos.size() >= MINIMO_DE_FOCOS].dropna().sort_values(ascending=False)
    else:
        nome_medida, unidade, casas = "número de focos", "focos", 0
        valores = grupos.size().sort_values(ascending=False)
    if valores.empty:
        return ""

    crescente = bool(re.search(r"\bmenos\b|\bmenor\b", texto)) or (
        assunto.crescente and not re.search(r"\bmais\b|\bmaior\b", texto)
    )
    if crescente:
        valores = valores.sort_values()
    ordem = next((n for t, n in ORDINAIS.items() if re.search(t, texto)), None)
    if "depois" in texto:
        ordem = assunto.posicao + 1
    posicao = ordem or 1
    assunto.crescente, assunto.posicao = crescente, posicao
    if posicao > len(valores):
        return ""
    chave = valores.index[posicao - 1]
    nome = f"{chave:%d/%m/%Y}" if assunto.nivel == "dia" else nome_proprio(str(chave))
    rotulo = {"municipio": "município"}.get(assunto.nivel, assunto.nivel)
    onde = f" em {nome_proprio(dentro[0][1])}" if dentro else " no Brasil"
    lugar = ["", "segundo ", "terceiro ", "quarto ", "quinto "][posicao - 1]
    sentido = "menor" if crescente else "maior"
    return (
        f"o {rotulo} com o {lugar}{sentido} {nome_medida}{onde} é {nome}, "
        f"com {numero(valores.iloc[posicao - 1], casas)} {unidade}".rstrip() + "."
    )


def destaque(assunto: Assunto, pergunta: str, focos: pd.DataFrame) -> str:
    """Conta já feita, para ir junto da pergunta: comparação, risco ou dia do lugar."""
    texto = normalizar(pergunta)
    if PERGUNTA_COMPARA.search(texto):
        itens = assunto.itens()
        if len(itens) < 2:
            # Os dois últimos lugares do mesmo tipo: um município citado no meio não conta.
            tipo = next((t for t, _ in assunto.recentes if t == "estado"), None) or (
                assunto.recentes[0][0] if assunto.recentes else None
            )
            itens = [i for i in assunto.recentes if i[0] == tipo][:2]
        menos = bool(re.search(r"\bmenos\b|\bmenor\b", texto))
        if comparadas := comparacoes(itens, focos, menos):
            return " ".join(comparadas)
    frases = [_ordem(assunto, pergunta, focos)] if SUPERLATIVO.search(texto) else []
    frases = [f for f in frases if f]
    # Conta pronta junto da pergunta: é o que o modelo pequeno menos erra.
    if re.search(r"prioriz|prioridade", texto):
        tres = focos["estado"].value_counts().head(3)
        frases.append(
            "Mais focos: "
            + "; ".join(f"{nome_proprio(e)} ({numero(n)})" for e, n in tres.items())
            + ". " + _estados_por_risco(focos)
        )
    do_dia = _dia_citado(texto, focos)
    if do_dia and not assunto.lugares:
        frases.append(
            f"Brasil em {do_dia:%d/%m/%Y}: {numero((focos['dia'] == do_dia).sum())} focos."
        )
    for coluna, nome in assunto.itens()[:3]:
        df = focos[focos[coluna] == nome]
        if df.empty:
            continue
        if do_dia:
            frases.append(
                f"{nome_proprio(nome)} em {do_dia:%d/%m/%Y}: {numero((df['dia'] == do_dia).sum())} focos."
            )
        elif re.search(r"quant[oa]s\b", texto) and not re.search(r"\bdias?\b|hectare", texto):
            frases.append(f"{nome_proprio(nome)}: {numero(len(df))} focos.")
        if re.search(r"risco|classe", assunto.texto):
            risco = df["risco_fogo"].dropna()
            frases.append(
                f"Risco de fogo em {nome_proprio(nome)}: "
                + (_risco(risco) if len(risco) else "sem valor informado pelo INPE") + "."
            )
        if re.search(r"\bdias?\b", texto) and "chuva" not in texto and "chove" not in texto:
            dias = df["dia"].value_counts()
            frases.append(
                f"Em {nome_proprio(nome)}, o dia com mais focos foi {dias.idxmax():%d/%m/%Y}, "
                f"com {numero(dias.max())}."
            )
    return " ".join(frases)


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


FUTURO_OU_PASSADO = re.compile(
    r"previsao|\bpreve|amanha|ontem|\bhoje\b|(semana|mes|ano) (que vem|passad[oa])|"
    r"proxim[oa]s? (dia|semana|mes|ano)|(dias|semanas|meses|anos) (atras|anteriores)|\bvai ter\b"
)
QUER_NOTICIA = re.compile(r"noticia|segundo [oa]s? (?!lugar|coloc)|imprensa|reportag|g1\b|agencia brasil")


PERGUNTA_FOCOS = re.compile(r"foco|quantas queimadas|quantos incendios|\bfrp\b|risco de fogo")


def fora_do_periodo(pergunta: str, focos: pd.DataFrame, anterior: Assunto | None) -> bool:
    """A pergunta é sobre os focos e cita data que eles não cobrem?"""
    # "Janeiro" também é parte de um lugar.
    _, texto = _achar(ESTADOS, normalizar(pergunta))
    if QUER_NOTICIA.search(texto) or TERMOS_NOTICIAS.search(texto):
        return False
    # "E em 2019?" continua o que se falava: focos ou notícias.
    continua = len(_termos(texto)) <= 2 and anterior is not None and not anterior.noticias
    if not (PERGUNTA_FOCOS.search(texto) or continua or FUTURO_OU_PASSADO.search(texto)):
        return False
    if FUTURO_OU_PASSADO.search(texto):
        return True
    dias = set(focos["dia"])
    for d, m, a in re.findall(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", texto):
        if not any(
            (x.day, x.month) == (int(d), int(m)) and (not a or x.year == int(a)) for x in dias
        ):
            return True
    if any(int(a) not in {x.year for x in dias} for a in re.findall(r"\b(?:19|20)\d\d\b", texto)):
        return True
    citados = {n for nome, n in MESES.items() if re.search(rf"\b{nome}\b", texto)}
    return bool(citados - {x.month for x in dias})


# Exceções do corte em 6 letras: sem elas, Amazonas e Amazônia seriam a mesma palavra.
SINONIMOS = {"crime": "crimin", "crimes": "crimin", "amazonas": "amazonas", "reabre": "reabri"}

VAZIAS = set(
    "a o as os e de do da dos das em no na nos nas um uma para por com que se qual quais quem "
    "como quando onde foi foram sao ser esta estao tem ha ao aos sobre mais me diga fale isso "
    "ele ela quantos quanto noticia noticias dizem diz queimada queimadas".split()
)


def _termos(texto: str) -> list[str]:
    # O corte em 6 letras junta variações simples (incêndio, incêndios, incendiário).
    return [
        SINONIMOS.get(p, p[:6])
        for p in re.findall(r"[a-z0-9]{3,}", normalizar(texto))
        if p not in VAZIAS
    ]


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
        # O título conta duas vezes: é o que melhor diz do que a notícia trata.
        self._contagens = [
            Counter(_termos(f"{t['titulo']} {t['titulo']} {t['texto']}")) for t in self.trechos
        ]
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
    if fora_do_periodo(pergunta, focos, memoria.assunto):
        assunto.recusa = "periodo"
    # O que sobra sem os lugares, as palavras de dados e as de quem continua a
    # conversa diz se o assunto é outro: "copa" e "restaurante" não estão em
    # notícia nenhuma sobre fogo.
    _, sobra = _achar([nome for _, nome in proprio.itens()], texto)
    sobra = " ".join(
        p for p in re.findall(r"[a-z]{3,}", sobra)
        if not TERMOS_DADOS.search(p) and not TERMOS_CONVERSA.match(p)
    )
    if not TERMOS_TEMA.search(texto) and _termos(sobra):
        proprios = trechos if consulta == pergunta else busca.buscar(pergunta, 3)
        if busca.cobertura(sobra, proprios) < COBERTURA_TEMA:
            assunto.recusa = "tema"
    if not assunto.noticias:
        # Pergunta numérica só leva notícia se tudo o que não é dado de foco
        # ("quanto a AGU cobra dos acusados") está junto em um mesmo trecho.
        outros = " ".join(
            p for p in re.findall(r"[a-z]{3,}", texto)
            if not TERMOS_DADOS.search(p) and not TERMOS_CONVERSA.match(p)
        )
        achou = len(_termos(outros)) >= 2 and busca.cobertura(outros, trechos) == 1
        trechos = trechos if achou else []
    if re.search(r"\bdados\b", texto) and "noticia" not in texto:
        trechos = []
    # Perguntou pelas notícias: sem os números dos focos, o modelo não os mistura.
    so_noticias = bool(re.search(r"noticia|imprensa|reportag", texto)) and trechos
    return assunto, [] if so_noticias else fatos(assunto, focos), trechos
