"""Testes da limpeza dos focos, do satélite de referência e das mensagens da página API."""

import ast
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "code"))

import app_utils  # noqa: E402
import base_dados  # noqa: E402


def test_codigo_de_ausencia_do_inpe_vira_vazio():
    df = pd.DataFrame(
        {
            "id": ["a", "b", "b"],
            "risco_fogo": [-999, 0.5, 0.5],
            "precipitacao": [0.0, -999, -999],
            "numero_dias_sem_chuva": [-999, 3, 3],
        }
    )
    limpo = base_dados.limpar_focos(df)
    assert len(limpo) == 2
    assert limpo["risco_fogo"].isna().tolist() == [True, False]
    assert limpo["precipitacao"].isna().tolist() == [False, True]
    assert limpo["numero_dias_sem_chuva"].isna().tolist() == [True, False]


def test_referencia_guarda_o_satelite_do_inpe_e_uploads_sem_satelite():
    df = pd.DataFrame({"satelite": ["AQUA_M-T", "NOAA-20", None]})
    assert len(app_utils.da_referencia(df)) == 2


def test_cada_artigo_fica_com_o_proprio_texto():
    artigos = base_dados.ler_artigos()
    assert len(artigos) == len(base_dados.ler_noticias())
    assert artigos["texto"].str.len().gt(0).all()


def test_noticias_com_sentimento_sao_as_coletadas():
    sentimento = pd.read_csv(base_dados.SENTIMENTO_CSV)
    assert set(sentimento["link"]) == set(base_dados.ler_noticias()["link"])


def carregar_explicar():
    """Só a função da página, sem executar o Streamlit."""
    arvore = ast.parse((RAIZ / "views" / "consulta_api.py").read_text(encoding="utf-8"))
    funcao = next(n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == "explicar")
    escopo = {}
    exec(compile(ast.Module([funcao], []), "consulta_api", "exec"), escopo)
    return escopo["explicar"]


def test_erro_422_vira_frase_em_portugues():
    explicar = carregar_explicar()
    detalhe = [
        {"loc": ["body", "texto"], "type": "string_too_short", "ctx": {"min_length": 20}},
        {"loc": ["body", "lat"], "type": "less_than_equal", "ctx": {"le": 90}},
    ]
    assert explicar(detalhe) == (
        "texto precisa de pelo menos 20 caracteres; lat deve ser no máximo 90."
    )
    assert explicar("já é texto") == "já é texto"
