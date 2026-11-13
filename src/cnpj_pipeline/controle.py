"""Tabela de controle: registra o que rodou, quando, com que resultado e quantas linhas."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from cnpj_pipeline.config import Settings
from cnpj_pipeline.warehouse import conectar

log = logging.getLogger(__name__)

DDL = """
CREATE SCHEMA IF NOT EXISTS ops;
CREATE TABLE IF NOT EXISTS ops.execucoes (
    run_id          VARCHAR,
    competencia     VARCHAR,
    etapa           VARCHAR,
    status          VARCHAR,
    linhas_arquivo  BIGINT,
    linhas_bronze   BIGINT,
    sha256          VARCHAR,
    iniciado_em     TIMESTAMP,
    finalizado_em   TIMESTAMP,
    mensagem        VARCHAR
);
"""


def _agora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def registrar(
    settings: Settings,
    *,
    run_id: str,
    competencia: str,
    etapa: str,
    status: str,
    iniciado_em: datetime,
    mensagem: str = "",
    metricas: dict | None = None,
) -> None:
    metricas = metricas or {}
    con = conectar(settings)
    try:
        con.execute(DDL)
        con.execute(
            "INSERT INTO ops.execucoes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                competencia,
                etapa,
                status,
                metricas.get("linhas_arquivo"),
                metricas.get("linhas_bronze"),
                metricas.get("sha256"),
                iniciado_em,
                _agora(),
                mensagem[:1000],
            ],
        )
    finally:
        con.close()


def executar_etapa(
    settings: Settings,
    *,
    run_id: str,
    competencia: str,
    etapa: str,
    funcao: Callable[[], dict],
) -> dict:
    """Executa a etapa, registra o resultado (sucesso ou falha) e repassa a exceção."""
    inicio = _agora()
    try:
        resultado = funcao()
    except Exception as erro:
        log.exception("Etapa %s falhou (competência %s)", etapa, competencia)
        registrar(
            settings,
            run_id=run_id,
            competencia=competencia,
            etapa=etapa,
            status="falha",
            iniciado_em=inicio,
            mensagem=f"{type(erro).__name__}: {erro}",
        )
        raise
    registrar(
        settings,
        run_id=run_id,
        competencia=competencia,
        etapa=etapa,
        status="sucesso",
        iniciado_em=inicio,
        metricas=resultado,
    )
    return resultado
