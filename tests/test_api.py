"""Testes da API. Rodar com o ambiente ativado: python -m pytest

Os modelos de linguagem são trocados por respostas fixas, então os testes
rodam em segundos e sem download. Para testar também os modelos reais, ligue
a variável TESTAR_MODELOS (comandos para cada sistema no README).
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from code import base_dados
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
    caminho = tmp_path / "focos_api.csv"
    monkeypatch.setattr(base_dados, "FOCOS_API_CSV", caminho)
    return caminho


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


def test_fila_ocupada_retorna_503_em_vez_de_504(modelos_falsos, monkeypatch):
    executor = ThreadPoolExecutor(max_workers=1)
    liberar = threading.Event()
    executor.submit(liberar.wait)
    monkeypatch.setattr(main, "_executor", executor)
    monkeypatch.setattr(main, "TEMPO_FILA_SEGUNDOS", 0.1)
    try:
        resposta = processar()
    finally:
        liberar.set()
        executor.shutdown()
    assert resposta.status_code == 503
    assert "ocupados" in resposta.json()["detail"]


def test_texto_que_comecou_no_limite_da_fila_e_respondido(modelos_falsos, monkeypatch):
    class JaComecou:
        """Espera da fila vence no mesmo instante em que o texto começa."""

        def set(self):
            pass

        def wait(self, timeout=None):
            while not inicio.is_set():
                time.sleep(0.01)
            return False

    inicio = threading.Event()

    def sentimento(texto):
        inicio.set()
        return sentimento_fixo(texto)

    monkeypatch.setattr(main, "threading", SimpleNamespace(Event=JaComecou))
    monkeypatch.setattr(llm, "analisar_sentimento", sentimento)
    assert processar().status_code == 200


def test_sem_dados_de_focos_retorna_503(csv_temporario, monkeypatch):
    monkeypatch.setattr(base_dados, "arquivos_focos", lambda incluir_api=False: [])
    resposta = cliente.get("/focos")
    assert resposta.status_code == 503
    assert "fetch_inpe.py" in resposta.json()["detail"]


def test_modelo_carregado_nao_espera_o_download_do_outro(monkeypatch):
    monkeypatch.setitem(llm._modelos, "sentimento", "modelo pronto")
    # Simula o resumo baixando: a trava dele fica ocupada durante o teste.
    with llm._travas["resumo"]:
        resultado = []
        t = threading.Thread(target=lambda: resultado.append(llm.carregar("sentimento")))
        t.start()
        t.join(timeout=2)
    assert resultado == ["modelo pronto"]


def test_saude_responde_sem_ler_dados():
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


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


def test_focos_gravados_por_fora_aparecem_sem_reiniciar(csv_temporario):
    assert cliente.get("/focos", params={"estado": "TESTE"}).json()["total_filtrado"] == 0
    csv_temporario.write_text(
        "id,lat,lon,estado,bioma\nx,-3.2,-52.1,TESTE,Amazônia\n", encoding="utf-8"
    )
    assert cliente.get("/focos", params={"estado": "TESTE"}).json()["total_filtrado"] == 1


def test_posts_simultaneos_gravam_um_cabecalho_so(csv_temporario):
    novo = {"lat": -3.2, "lon": -52.1, "estado": "teste"}
    threads = [
        threading.Thread(target=cliente.post, args=("/focos",), kwargs={"json": novo})
        for _ in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    linhas = csv_temporario.read_text(encoding="utf-8").splitlines()
    assert sum(linha.startswith("id,") for linha in linhas) == 1
    assert len(linhas) == 11


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
