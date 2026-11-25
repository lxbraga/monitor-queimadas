"""Avalia o assistente com conversas de gabarito conhecido.

As conversas estão em data/processed/avaliacao_assistente.json. As de
desenvolvimento servem para ajustar o prompt; as de teste só medem o resultado.
Os gabaritos valem para os arquivos de 19 a 21/09/2026, versionados no projeto.

Compara o prompt em uso com versões sem partes dele, para mostrar o que cada
parte contribui. Rodar da raiz do projeto:
    python -m code.modeling.avaliar_assistente [desenvolvimento|teste] [variante ...] [-v]
"""

from __future__ import annotations

import json
import re
import sys
import time

import pandas as pd

from code import analise, assistente, base_dados

CONJUNTO = base_dados.DATA_DIR / "processed" / "avaliacao_assistente.json"
DIAS = ("20260919", "20260920", "20260921")
RECUSA = re.compile(
    r"não encontrei|não (há|tenho|possuo|existem?|foram encontrad)|não est(á|ão)|não posso|"
    r"não é possível|não inclu|não (fornece|menciona|consta)|fora do",
    re.I,
)
VARIANTES = ["completo", "sem_regras", "sem_material", "sem_memoria"]


def mensagens(variante, pergunta, fatos, trechos, memoria, destaque):
    if variante == "sem_material":
        return [
            {"role": "system", "content": assistente.PAPEL},
            *memoria.recentes(), {"role": "user", "content": pergunta},
        ]
    montadas = assistente.montar_mensagens(pergunta, fatos, trechos, memoria, destaque)
    if variante == "sem_regras":
        montadas[0]["content"] = montadas[0]["content"].replace(assistente.REGRAS + "\n\n", "")
        montadas[-1]["content"] = "\n\n".join(filter(None, [pergunta, destaque]))
    return montadas


# O material de focos não traz nada disto; se aparece, o modelo inventou.
INVENCAO = re.compile(
    r"últim[ao]s [^.]{0,20}horas|início do mês|em relação ao (ano|mês)|(ano|mês) passado|"
    r"aumento significativo",
    re.I,
)


def acertou(turno: dict, resposta: str, trechos: list[dict], sem_origem: list[str]) -> bool:
    if turno.get("recusa"):
        # Recusar e emendar um número inventado não é recusar.
        return bool(RECUSA.search(resposta)) and not sem_origem
    if any(re.search(p, resposta, re.I) for p in turno.get("proibido", [])):
        return False
    if not trechos and INVENCAO.search(resposta):
        return False
    return all(re.search(p, resposta, re.I) for p in turno["esperado"])


def main() -> int:
    argumentos = [a for a in sys.argv[1:] if a != "-v"]
    parte = argumentos[0] if argumentos else "teste"
    variantes = argumentos[1:] or VARIANTES
    focos = base_dados.ler_focos(
        [a for a in base_dados.arquivos_focos() if a.stem.endswith(DIAS)]
    )
    focos = focos[focos["satelite"] == base_dados.SATELITE_REFERENCIA].copy()
    focos["dia"] = pd.to_datetime(focos["data_hora_gmt"]).dt.date
    busca = analise.BuscaNoticias(base_dados.ler_artigos())
    gerador = assistente.Gerador()
    print(f"{assistente.MODELO} em {gerador.dispositivo}; conversas de {parte}")
    conversas = [c for c in json.loads(CONJUNTO.read_text(encoding="utf-8")) if c["parte"] == parte]

    linhas = []
    for variante in variantes:
        for n, conversa in enumerate(conversas):
            memoria = assistente.Memoria()
            for turno in conversa["turnos"]:
                if variante == "sem_memoria":
                    memoria = assistente.Memoria()
                assunto, fatos, trechos = analise.reunir(
                    turno["pergunta"], focos, busca, memoria
                )
                msgs = mensagens(
                    variante, turno["pergunta"], fatos, trechos, memoria,
                    analise.destaque(assunto, turno["pergunta"], focos),
                )
                inicio = time.perf_counter()
                if assunto.fora_do_tema and variante == "completo":
                    resposta = assistente.FORA_DO_TEMA
                else:
                    resposta = "".join(gerador.gerar(msgs)).strip()
                duracao = time.perf_counter() - inicio
                conversa_recente = memoria.ultimas_respostas()
                memoria.adicionar(turno["pergunta"], resposta)
                memoria.assunto = assunto
                analise.aprender_da_resposta(assunto, turno["pergunta"], resposta, focos)
                material = "\n".join(m["content"] for m in msgs)
                _, sem_origem = assistente.conferir_numeros(
                    resposta, material, conversa_recente
                )
                # As regras do prompt citam "aumento"; o material são fatos e notícias.
                tendencia = assistente.conferir_tendencia(
                    resposta, "\n".join(fatos) + assistente.formatar_noticias(trechos)
                )
                linhas.append(
                    {"parte": parte, "variante": variante, "conversa": n, "tipo": turno["tipo"],
                     "pergunta": turno["pergunta"], "resposta": resposta,
                     "acertou": acertou(turno, resposta, trechos, sem_origem),
                     "numeros_sem_origem": " ".join(sem_origem),
                     "tendencia_sem_base": tendencia or "", "segundos": round(duracao, 2)}
                )
                if linhas[-1]["acertou"] and "-v" not in sys.argv:
                    continue
                marca = "ok  " if linhas[-1]["acertou"] else "ERRO"
                print(f"{marca} [{variante}/{turno['tipo']}] {turno['pergunta']} -> {resposta[:300]!r}"
                      + (f" (sem origem: {sem_origem})" if sem_origem else "")
                      + (f" (tendência sem base: {tendencia})" if tendencia else ""), flush=True)

    tabela = pd.DataFrame(linhas)
    destino = base_dados.DATA_DIR / "processed" / f"resultado_avaliacao_assistente_{parte}.csv"
    tabela.to_csv(destino, index=False)
    resumo = tabela.pivot_table(
        index="variante", columns="tipo", values="acertou", aggfunc=["sum", "count"]
    )
    print("\nAcertos por tipo:\n" + resumo["sum"].to_string())
    print("\nPerguntas por tipo:\n" + resumo["count"].iloc[:1].to_string())
    geral = tabela.groupby("variante").agg(
        acertos=("acertou", "sum"), total=("acertou", "size"),
        respostas_com_numero_sem_origem=("numeros_sem_origem", lambda s: (s != "").sum()),
        respostas_com_tendencia_sem_base=("tendencia_sem_base", lambda s: (s != "").sum()),
        mediana_s=("segundos", "median"), max_s=("segundos", "max"),
    )
    print("\n" + geral.to_string())
    print(f"\nRespostas completas em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
