"""Testes do desempate utilizado na camada Silver."""

import re
from pathlib import Path

import duckdb

MODELO = (
    Path(__file__).resolve().parents[1]
    / "dbt/models/silver/stg_empresas.sql"
)


def _ordenacao_do_modelo():
    sql = MODELO.read_text(encoding="utf-8")
    trecho = re.search(
        r"row_number\(\) over\s*\(.*?order by(.*?)\)\s+as _ordem",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert trecho, "Ordenacao de deduplicacao nao encontrada no modelo Silver"
    return trecho.group(1).strip()


def _escolher_registro(registros):
    con = duckdb.connect(":memory:")
    try:
        con.execute("""
            CREATE TABLE origem (
                cnpj_basico VARCHAR,
                razao_social VARCHAR,
                natureza_juridica VARCHAR,
                qualificacao_responsavel VARCHAR,
                capital_social VARCHAR,
                porte_empresa VARCHAR,
                ente_federativo_responsavel VARCHAR,
                _carregado_em TIMESTAMP,
                _run_id VARCHAR,
                _sha256 VARCHAR,
                _arquivo VARCHAR
            )
        """)
        con.executemany(
            "INSERT INTO origem VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            registros,
        )
        ordenacao = _ordenacao_do_modelo()
        return con.execute(f"""
            SELECT razao_social
            FROM (
                SELECT
                    razao_social,
                    ROW_NUMBER() OVER (
                        PARTITION BY lpad(trim(cnpj_basico), 8, '0')
                        ORDER BY {ordenacao}
                    ) AS posicao
                FROM origem
            )
            WHERE posicao = 1
        """).fetchone()[0]
    finally:
        con.close()


def _registro(nome, data, run_id, arquivo="Empresas0.zip"):
    return (
        "12345678", nome, "2062", "49", "1000,00",
        "01", "", data, run_id, "hash", arquivo,
    )


def test_prefere_carga_mais_recente():
    registros = [
        _registro("ANTIGA", "2026-10-01 10:00:00", "run_a"),
        _registro("RECENTE", "2026-10-02 10:00:00", "run_b"),
    ]
    assert _escolher_registro(registros) == "RECENTE"
    assert _escolher_registro(list(reversed(registros))) == "RECENTE"


def test_desempate_por_run_id():
    registros = [
        _registro("VERSAO_A", "2026-10-01 10:00:00", "run_a"),
        _registro("VERSAO_B", "2026-10-01 10:00:00", "run_b"),
    ]
    assert _escolher_registro(registros) == "VERSAO_B"
    assert _escolher_registro(list(reversed(registros))) == "VERSAO_B"


def test_desempate_por_campos_de_negocio():
    registros = [
        _registro("EMPRESA A", "2026-10-01 10:00:00", "run_a"),
        _registro("EMPRESA B", "2026-10-01 10:00:00", "run_a"),
    ]
    assert _escolher_registro(registros) == "EMPRESA B"
    assert _escolher_registro(list(reversed(registros))) == "EMPRESA B"
