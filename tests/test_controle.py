import pytest

pytest.importorskip("duckdb")

from cnpj_pipeline.controle import executar_etapa
from cnpj_pipeline.warehouse import conectar


def test_registra_erro_e_propaga_excecao(settings):
    def falhar():
        raise ValueError("falha controlada")

    with pytest.raises(ValueError, match="falha controlada"):
        executar_etapa(
            settings,
            run_id="run-teste-falha",
            competencia="2026-10",
            etapa="bronze",
            funcao=falhar,
        )

    con = conectar(settings, read_only=True)
    try:
        linhas = con.execute(
            "SELECT status, mensagem FROM ops.execucoes WHERE run_id = ?",
            ["run-teste-falha"],
        ).fetchall()
    finally:
        con.close()
    assert linhas == [("falha", "ValueError: falha controlada")]


def test_registra_sucesso_com_metricas(settings):
    retorno = executar_etapa(
        settings,
        run_id="run-teste-sucesso",
        competencia="2026-10",
        etapa="bronze",
        funcao=lambda: {"linhas_arquivo": 4, "linhas_bronze": 4, "sha256": "abc"},
    )
    assert retorno["linhas_bronze"] == 4

    con = conectar(settings, read_only=True)
    try:
        linhas = con.execute(
            "SELECT status, linhas_arquivo, linhas_bronze, sha256 "
            "FROM ops.execucoes WHERE run_id = ?",
            ["run-teste-sucesso"],
        ).fetchall()
    finally:
        con.close()
    assert linhas == [("sucesso", 4, 4, "abc")]
