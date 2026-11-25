"""Testes do assistente sem carregar o modelo: fatos, busca, memória e conferência."""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import analise  # noqa: E402
import assistente  # noqa: E402


@pytest.fixture
def focos():
    linhas = [("PARÁ", "Amazônia", "ALTAMIRA")] * 3 + [("TOCANTINS", "Cerrado", "ARAGUAÍNA")] * 2
    df = pd.DataFrame(linhas, columns=["estado", "bioma", "municipio"])
    df["frp"], df["risco_fogo"], df["numero_dias_sem_chuva"] = 10.0, 0.9, 5
    df["dia"] = date(2026, 9, 19)
    return df


@pytest.fixture
def busca():
    return analise.BuscaNoticias(
        pd.DataFrame(
            {
                "titulo": ["Fumaça cobre Manaus", "Desmatamento cai na Mata Atlântica"],
                "fonte": ["G1", "Agência Brasil"],
                "data": ["01/10/2026", "01/08/2024"],
                "link": ["a", "b"],
                "texto": ["A fumaça cobriu Manaus por dez dias.", "O desmatamento caiu 55%."],
            }
        )
    )


def test_numero_no_formato_brasileiro():
    assert analise.numero(1234.5, 1) == "1.234,5"


@pytest.mark.parametrize(
    "pergunta, estados",
    [
        ("Quantos focos no Pará?", ["PARÁ"]),
        ("Quantos focos para o Tocantins?", ["TOCANTINS"]),
        ("E em Mato Grosso do Sul?", ["MATO GROSSO DO SUL"]),
    ],
)
def test_identifica_o_estado_citado(focos, pergunta, estados):
    assert analise.identificar(pergunta, focos).estados == estados


def test_pergunta_sem_lugar_herda_o_da_anterior(focos):
    anterior = analise.identificar("Quantos focos no Pará?", focos)
    assert analise.identificar("E o risco de fogo?", focos, anterior).estados == ["PARÁ"]


def test_resposta_com_um_lugar_vira_o_assunto(focos):
    pergunta = "Qual estado teve mais focos?"
    assunto = analise.identificar(pergunta, focos)
    analise.aprender_da_resposta(assunto, pergunta, "O Pará, com 3 focos.", focos)
    assert assunto.estados == ["PARÁ"]


def test_fatos_do_lugar_vem_antes_e_com_a_conta_certa(focos):
    assunto = analise.identificar("Quantos focos no Pará?", focos)
    primeiro = analise.fatos(assunto, focos)[0]
    assert primeiro.startswith("Estado Pará: 3 focos, 60,0% do Brasil")


def test_destaque_compara_os_ultimos_lugares(focos):
    um = analise.identificar("Focos no Pará?", focos)
    dois = analise.identificar("E no Tocantins?", focos, um)
    frase = analise.destaque(dois, "Qual dos dois teve mais?", focos)
    assert "Pará teve mais focos (3) que Tocantins (2); a diferença é 1" in frase


@pytest.mark.parametrize(
    "pergunta, recusa",
    [
        ("Quantos focos houve em janeiro de 2020?", "periodo"),
        ("Quantos focos houve em 01/01/2026?", "periodo"),
        ("Vai ter mais fogo na semana que vem?", "periodo"),
        ("Quantos focos houve em 19/09/2026?", ""),
        ("O que as notícias dizem sobre as queimadas de 2024?", ""),
    ],
)
def test_data_fora_da_base_e_recusada(focos, busca, pergunta, recusa):
    assert analise.reunir(pergunta, focos, busca, assistente.Memoria())[0].recusa == recusa


def test_assunto_estranho_e_recusado_no_meio_da_conversa(focos, busca):
    memoria = assistente.Memoria()
    pergunta = "Qual estado teve mais focos?"
    memoria.assunto = analise.reunir(pergunta, focos, busca, memoria)[0]
    memoria.adicionar(pergunta, "O Pará.")
    assert analise.reunir("Quem ganhou a Copa?", focos, busca, memoria)[0].recusa == "tema"
    assert analise.reunir("E o segundo?", focos, busca, memoria)[0].recusa == ""


def test_posicao_pedida_e_calculada(focos):
    um = analise.identificar("Qual estado teve mais focos?", focos)
    assert "é Pará, com 3 focos" in analise.destaque(um, "Qual estado teve mais focos?", focos)
    dois = analise.identificar("E o segundo?", focos, um)
    assert "é Tocantins, com 2 focos" in analise.destaque(dois, "E o segundo?", focos)
    menos = analise.identificar("Qual bioma teve menos focos?", focos)
    assert "é Cerrado" in analise.destaque(menos, "Qual bioma teve menos focos?", focos)


def test_risco_vai_com_a_classe_e_sem_a_palavra_medio(focos):
    fato = analise.fatos_do_lugar("PARÁ", "estado", focos)
    assert "classe ALTO (índice 0,90 de 1)" in fato and "risco de fogo médio" not in fato


@pytest.mark.parametrize(
    "valor, classe", [(0.1, "mínimo"), (0.4, "baixo"), (0.7, "médio"), (0.95, "alto"), (1, "crítico")]
)
def test_classes_de_risco(valor, classe):
    assert analise.classe_de_risco(valor) == classe


def test_busca_traz_a_noticia_do_assunto(busca):
    assert busca.buscar("fumaça em Manaus")[0]["link"] == "a"


def test_reunir_marca_pergunta_fora_do_tema(focos, busca):
    memoria = assistente.Memoria()
    assunto, _, _ = analise.reunir("Quem ganhou a Copa do Mundo?", focos, busca, memoria)
    assert assunto.recusa == "tema"
    assunto, _, _ = analise.reunir("Quantos focos no Pará?", focos, busca, memoria)
    assert not assunto.recusa


def test_noticia_filtrada_por_mes_e_ano():
    trechos = [{"data": "01/10/2026"}, {"data": "01/08/2024"}]
    assert analise.da_data(trechos, "notícias de agosto de 2024") == [trechos[1]]
    assert analise.da_data(trechos, "notícias de 2024") == trechos


def test_memoria_mantem_a_janela_e_resume_o_resto():
    memoria = assistente.Memoria()
    for i in range(assistente.JANELA + 1):
        memoria.adicionar(f"pergunta {i}", f"resposta {i}. Detalhe.")
    assert len(memoria.recentes()) == assistente.JANELA * 2
    assert memoria.antigas() == "- Perguntou: pergunta 0 Você respondeu: resposta 0."


def test_prompt_leva_regras_dados_e_noticias(busca):
    mensagens = assistente.montar_mensagens(
        "E a fumaça?", ["Total: 5 focos."], busca.buscar("fumaça"), assistente.Memoria()
    )
    sistema = mensagens[0]["content"]
    assert "Regras:" in sistema and "Total: 5 focos." in sistema
    assert "[G1, 01/10/2026]" in sistema
    assert mensagens[-1]["content"].startswith("E a fumaça?")


def test_confere_numeros_da_resposta():
    material = "Pará, 1.060 focos; Amazonas, 696 focos."
    assert assistente.conferir_numeros("São 1.060 e 696, somando 1.756.", material) == (
        ["1.756"], []
    )
    assert assistente.conferir_numeros("Foram 999 focos.", material) == ([], ["999"])


def test_confere_tendencia_que_o_material_nao_mede():
    assert assistente.conferir_tendencia("Houve aumento dos focos.", "Pará, 10 focos.") == "aumento"
    assert assistente.conferir_tendencia("Houve aumento.", "A alta foi de 10%.") is None
