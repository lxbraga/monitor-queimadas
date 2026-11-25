"""Assistente conversacional com memória, sobre os focos e as notícias.

O modelo roda localmente, via Transformers. A cada pergunta ele recebe os fatos
calculados em analise.py, os trechos de notícias encontrados e a memória da
conversa, e os números da resposta são conferidos contra esse material.
"""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass, field

# Máquinas com pouca memória podem usar Qwen/Qwen2.5-0.5B-Instruct.
MODELO = os.environ.get("MODELO_ASSISTENTE", "Qwen/Qwen2.5-1.5B-Instruct")
MAX_TOKENS_RESPOSTA = 260

# Trocas recentes que vão inteiras para o modelo; as mais antigas, resumidas.
JANELA = 5
MAX_ANTIGAS = 8

PAPEL = (
    "Você é o assistente do Monitor de Queimadas e responde a gestores públicos, ONGs e "
    "jornalistas sobre queimadas no Brasil, em português do Brasil."
)
NAO_ENCONTREI = "Não encontrei essa informação nos dados do projeto."


def recusar(motivo: str, inicio, fim) -> str:
    """Resposta dada por código, sem o modelo, quando a pergunta não tem como ser respondida."""
    if motivo == "periodo":
        return (
            f"Só tenho focos de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}; não encontrei essa data nos "
            "dados. Para outras épocas, pergunte o que as notícias dizem."
        )
    return (
        NAO_ENCONTREI + " Posso responder sobre os focos de calor do período carregado e "
        "sobre as notícias de queimadas coletadas."
    )


REGRAS = """Regras:
1. Use somente o material abaixo (DADOS e NOTÍCIAS) e a conversa. Não use outro conhecimento.
2. Copie números, nomes e datas exatamente como estão no material. Não faça estimativas.
3. DADOS são focos de calor do INPE, só do período indicado. NOTÍCIAS são de outras datas: não misture os números dos dois.
4. Se a resposta não estiver no material, diga "Não encontrei essa informação nos dados do projeto." e não complete com suposições.
5. Se usar uma notícia, cite a fonte e a data dela.
6. Não fale em aumento, queda, horas, semanas ou meses se o material não disser isso.
7. Responda direto, em até 4 frases curtas."""

# Repetido junto da pergunta: modelos pequenos seguem melhor o que está perto do fim.
LEMBRETE = (
    "(Responda em frases completas, só com números e fatos que estão no material ou na "
    "conversa. Se a resposta não estiver lá, diga que não encontrou essa informação.)"
)


@dataclass
class Memoria:
    """Trocas da conversa e o assunto atual."""

    trocas: list[tuple[str, str]] = field(default_factory=list)
    assunto: object | None = None

    def adicionar(self, pergunta: str, resposta: str) -> None:
        self.trocas.append((pergunta, resposta))

    def recentes(self) -> list[dict]:
        mensagens = []
        for pergunta, resposta in self.trocas[-JANELA:]:
            mensagens.append({"role": "user", "content": pergunta})
            mensagens.append({"role": "assistant", "content": resposta})
        return mensagens

    def ultimas_respostas(self) -> str:
        return "\n".join(resposta for _, resposta in self.trocas[-2:])

    def antigas(self) -> str:
        """Uma linha por troca que saiu da janela: a pergunta e a 1ª frase da resposta."""
        linhas = []
        for pergunta, resposta in self.trocas[:-JANELA][-MAX_ANTIGAS:]:
            primeira = re.split(r"(?<=[.!?])\s", resposta.strip())[0][:200]
            linhas.append(f"- Perguntou: {pergunta} Você respondeu: {primeira}")
        return "\n".join(linhas)


def formatar_noticias(trechos: list[dict]) -> str:
    return "\n\n".join(
        f"[{t['fonte']}, {t['data']}] {t['titulo']}\n{t['texto']}" for t in trechos
    )


def montar_mensagens(
    pergunta: str, fatos: list[str], trechos: list[dict], memoria: Memoria, destaque: str = ""
) -> list[dict]:
    blocos = [PAPEL, REGRAS]
    if fatos:
        blocos.append("DADOS (focos de calor, satélite de referência do INPE):\n" + "\n".join(fatos))
    if trechos:
        blocos.append("NOTÍCIAS:\n" + formatar_noticias(trechos))
    if antigas := memoria.antigas():
        blocos.append("Início da conversa:\n" + antigas)
    if destaque:
        destaque = f"(Dado calculado para esta pergunta, use-o na resposta: {destaque})"
    return [
        {"role": "system", "content": "\n\n".join(blocos)},
        *memoria.recentes(),
        {"role": "user", "content": "\n\n".join(filter(None, [pergunta, destaque, LEMBRETE]))},
    ]


NUMERO = re.compile(r"\d+(?:\.\d{3})+(?:,\d+)?|\d+[.,]\d+|\d+")


def _valor(texto: str) -> float:
    if re.fullmatch(r"\d+(\.\d{3})+(,\d+)?", texto):
        texto = texto.replace(".", "")
    return float(texto.replace(",", "."))


def numeros(texto: str) -> dict[float, str]:
    # Marcadores de lista e ordinais não são dados.
    texto = re.sub(r"(?m)^\s*\d+[.)]\s|\d+[ºª]", " ", texto)
    return {_valor(m): m for m in NUMERO.findall(texto)}


TENDENCIA = re.compile(
    r"\b(aument\w*|cresc\w*|alta\b|diminu\w*|redu[zç]\w*|queda|caiu|caíram|subiu|subiram|"
    r"piorou|melhorou|recorde)",
    re.I,
)


def conferir_tendencia(resposta: str, material: str) -> str | None:
    """Palavra de tendência da resposta que o material não usa."""
    achado = TENDENCIA.search(resposta)
    return achado.group() if achado and not TENDENCIA.search(material) else None


def conferir_numeros(
    resposta: str, material: str, conversa: str = ""
) -> tuple[list[str], list[str]]:
    """Números da resposta que não estão no material.

    Devolve (derivados, sem_origem). Derivado é o que sai de uma conta simples
    (soma, diferença, razão ou percentual) entre dois números do material que a
    resposta ou a conversa recente citam.
    """
    conhecidos = set(numeros(material))
    citados = numeros(resposta)
    base = {v for v in (*citados, *numeros(conversa)) if v in conhecidos}
    derivados, sem_origem = [], []
    for valor, texto in citados.items():
        if valor in conhecidos:
            continue
        contas = (
            conta
            for a in base
            for b in base
            if a != b
            for conta in (a + b, a - b, a / b if b else 0, a / b * 100 if b else 0)
        )
        perto = any(abs(valor - c) <= max(0.06, abs(c) * 0.005) for c in contas)
        (derivados if perto else sem_origem).append(texto)
    return derivados, sem_origem


class Gerador:
    """Carrega o modelo uma vez e gera uma resposta por vez."""

    def __init__(self, modelo: str = MODELO):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if torch.cuda.is_available():
            self.dispositivo, tipo = "cuda", torch.float16
        elif torch.backends.mps.is_available():
            self.dispositivo, tipo = "mps", torch.float16
        else:
            self.dispositivo, tipo = "cpu", torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(modelo)
        self.modelo = AutoModelForCausalLM.from_pretrained(modelo, dtype=tipo).to(self.dispositivo)
        self._trava = threading.Lock()

    def gerar(self, mensagens: list[dict]):
        """Produz a resposta em pedaços, conforme o modelo escreve."""
        from transformers import TextIteratorStreamer

        entrada = self.tokenizer.apply_chat_template(
            mensagens, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self.dispositivo)
        saida = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        erros: list[Exception] = []

        def executar():
            try:
                with self._trava:
                    self.modelo.generate(
                        **entrada, streamer=saida, do_sample=False,
                        max_new_tokens=MAX_TOKENS_RESPOSTA,
                        # Os padrões de amostragem do modelo só geram aviso sem do_sample.
                        temperature=None, top_p=None, top_k=None,
                    )
            except Exception as exc:
                erros.append(exc)
                saida.end()

        thread = threading.Thread(target=executar, daemon=True)
        thread.start()
        yield from saida
        thread.join()
        if erros:
            raise RuntimeError(f"O modelo falhou ao responder: {erros[0]}") from erros[0]
