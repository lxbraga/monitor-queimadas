"""Testes da API. Rodar com: .venv/bin/python -m pytest

Os modelos de linguagem são trocados por respostas fixas, então os testes
rodam em segundos e sem download. Para testar também os modelos reais:
TESTAR_MODELOS=1 .venv/bin/python -m pytest
"""

import os
import time

import pytest
from fastapi.testclient import TestClient

from code.api import llm, main

cliente = TestClient(main.app)
TEXTO = "A fumaça das queimadas cobriu a cidade e os atendimentos dispararam."


def sentimento_fixo(texto):
    return {
        "resultado": {"rotulo": "negativo", "confianca": 0.9},
        "tokens_entrada": 20,
        "truncado": False,
    }


def resumo_fixo(texto):
    return {
        "resultado": {"resumo": "Fumaça das queimadas lota postos de saúde."},
        "tokens_entrada": 20,
        "truncado": False,
    }


@pytest.fixture
def modelos_falsos(monkeypatch):
    monkeypatch.setattr(llm, "carregar", lambda tarefa: None)
    monkeypatch.setattr(llm, "analisar_sentimento", sentimento_fixo)
    monkeypatch.setattr(llm, "resumir", resumo_fixo)


@pytest.fixture
def csv_temporario(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "API_CSV", tmp_path / "focos_api.csv")
    main.carregar_focos.cache_clear()
    yield main.API_CSV
    main.carregar_focos.cache_clear()


def processar(texto=TEXTO, tipo="sentimento"):
    return cliente.post(
        "/processar_texto", json={"texto": texto, "tipo_analise": tipo}
    )


def test_sentimento_responde_no_formato_do_modelo(modelos_falsos):
    resposta = processar()
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo_analise"] == "sentimento"
    assert corpo["modelo"] == llm.MODELO_SENTIMENTO
    assert corpo["resultado"] == {"rotulo": "negativo", "confianca": 0.9}
    assert corpo["truncado"] is False
    assert corpo["tempo_segundos"] >= 0


def test_resumo_responde_no_formato_do_modelo(modelos_falsos):
    resposta = processar(tipo="resumo")
    assert resposta.status_code == 200
    assert resposta.json()["resultado"]["resumo"].startswith("Fumaça")


def test_texto_curto_retorna_422(modelos_falsos):
    assert processar(texto="curto").status_code == 422


def test_tipo_de_analise_invalido_retorna_422(modelos_falsos):
    assert processar(tipo="tradução").status_code == 422


def test_texto_so_com_espacos_retorna_400(modelos_falsos):
    resposta = processar(texto=" " * 30)
    assert resposta.status_code == 400
    assert "espaços" in resposta.json()["detail"]


def test_modelo_que_nao_carrega_retorna_503(modelos_falsos, monkeypatch):
    def falha(tarefa):
        raise OSError("sem conexão")

    monkeypatch.setattr(llm, "carregar", falha)
    resposta = processar()
    assert resposta.status_code == 503
    assert "sem conexão" in resposta.json()["detail"]


def test_falha_no_processamento_retorna_500(modelos_falsos, monkeypatch):
    def falha(texto):
        raise RuntimeError("tensor inválido")

    monkeypatch.setattr(llm, "analisar_sentimento", falha)
    resposta = processar()
    assert resposta.status_code == 500
    assert "tensor inválido" in resposta.json()["detail"]


def test_processamento_lento_retorna_504(modelos_falsos, monkeypatch):
    def lento(texto):
        time.sleep(1)
        return sentimento_fixo(texto)

    monkeypatch.setattr(llm, "analisar_sentimento", lento)
    monkeypatch.setattr(main, "TEMPO_LIMITE_SEGUNDOS", 0.1)
    assert processar().status_code == 504


def test_get_focos_filtra_por_estado():
    resposta = cliente.get("/focos", params={"estado": "pará", "limite": 3})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["focos"]) == 3
    assert corpo["total_filtrado"] >= 3
    assert all(f["estado"] == "PARÁ" for f in corpo["focos"])


def test_get_noticias_filtra_por_fonte():
    corpo = cliente.get("/noticias", params={"fonte": "G1"}).json()
    assert corpo["total"] > 0
    assert all(n["fonte"] == "G1" for n in corpo["noticias"])


def test_post_foco_grava_e_aparece_na_consulta(csv_temporario):
    novo = {"lat": -3.2, "lon": -52.1, "estado": "teste", "bioma": "Amazônia"}
    resposta = cliente.post("/focos", json=novo)
    assert resposta.status_code == 201
    assert csv_temporario.exists()
    consulta = cliente.get("/focos", params={"estado": "TESTE"}).json()
    assert consulta["total_filtrado"] == 1


def test_post_foco_com_coordenada_invalida_retorna_422(csv_temporario):
    resposta = cliente.post("/focos", json={"lat": 999, "lon": 0, "estado": "PA"})
    assert resposta.status_code == 422
    assert not csv_temporario.exists()


@pytest.mark.skipif(
    not os.environ.get("TESTAR_MODELOS"),
    reason="baixa e roda os modelos reais; use TESTAR_MODELOS=1",
)
@pytest.mark.parametrize("tipo", ["sentimento", "resumo"])
def test_modelos_reais(tipo):
    texto = (
        "A fumaça das queimadas cobriu Manaus por dez dias seguidos e os "
        "atendimentos por problemas respiratórios dispararam nas unidades de saúde."
    )
    resposta = processar(texto=texto, tipo=tipo)
    assert resposta.status_code == 200
    assert resposta.json()["truncado"] is False
