"""Testes da validação de CSVs enviados pela página Dados."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from app_utils import validar_upload  # noqa: E402

LINHA_VALIDA = {
    "lat": "-11.34",
    "lon": "-51.33",
    "data_hora_gmt": "2026-09-18 00:00:00",
    "municipio": "TESTE",
    "estado": "MATO GROSSO",
    "bioma": "Cerrado",
    "frp": "56.1",
}


def csv_com(**alteracoes):
    return pd.DataFrame([{**LINHA_VALIDA, **alteracoes}])


def test_csv_valido_volta_pronto_para_somar():
    df, erro = validar_upload(csv_com())
    assert erro is None
    assert df["lat"].iloc[0] == -11.34
    assert str(df["dia"].iloc[0]) == "2026-09-18"


def test_frp_vazio_e_aceito():
    df, erro = validar_upload(csv_com(frp=None))
    assert erro is None
    assert df["frp"].isna().all()


def test_coluna_faltando_e_recusada():
    df, erro = validar_upload(csv_com().drop(columns=["bioma"]))
    assert df is None
    assert "bioma" in erro


def test_arquivo_sem_linhas_e_recusado():
    df, erro = validar_upload(csv_com().iloc[0:0])
    assert df is None
    assert "nenhuma linha" in erro


def test_data_invalida_e_recusada():
    df, erro = validar_upload(csv_com(data_hora_gmt="ontem"))
    assert df is None
    assert "data_hora_gmt" in erro


def test_coordenada_fora_do_intervalo_e_recusada():
    df, erro = validar_upload(csv_com(lat="95"))
    assert df is None
    assert "lat" in erro


def test_frp_com_texto_e_recusado():
    df, erro = validar_upload(csv_com(frp="alto"))
    assert df is None
    assert "frp" in erro
