"""DAG mensal do CNPJ (Empresas0): extração -> bronze -> dbt silver -> dbt gold.

A competência (AAAA-MM) pode ser informada ao disparar a DAG. Sem ela, vale o mês da
execução agendada. Reprocessar uma competência é disparar a DAG com o parâmetro.
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta

from airflow.sdk import Param, dag, get_current_context, task

log = logging.getLogger(__name__)

DBT_BIN = "/opt/dbt-venv/bin/dbt"
DBT_DIR = "/opt/airflow/dbt"

# Agendamento mensal só faz sentido com a URL da Receita; com arquivo local, execução manual.
AGENDAMENTO = "0 6 12 * *" if os.environ.get("CNPJ_SOURCE_URL") else None


def _executar_dbt(selecao: str, competencia: str) -> None:
    """Roda `dbt build` para a seleção informada, mostrando a saída em tempo real."""
    comando = [
        "nice",
        "-n",
        "10",  # prioridade menor: o Airflow continua responsivo durante a transformação
        DBT_BIN,
        "build",
        "--select",
        selecao,
        "--indirect-selection",
        "buildable",
        "--project-dir",
        DBT_DIR,
        "--profiles-dir",
        DBT_DIR,
        "--target-path",
        "/tmp/dbt_target",
        "--log-path",
        "/tmp/dbt_logs",
        "--vars",
        json.dumps({"competencia": competencia}),
    ]
    processo = subprocess.Popen(
        comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    for linha in processo.stdout:
        print(linha, end="", flush=True)
    codigo = processo.wait()
    if codigo != 0:
        raise RuntimeError(f"dbt build ({selecao}) terminou com código {codigo}. Veja o log acima.")


@dag(
    dag_id="cnpj_empresas",
    schedule=AGENDAMENTO,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    params={
        "competencia": Param(
            None,
            type=["null", "string"],
            description="Competência AAAA-MM. Vazio: mês da execução.",
        ),
        "forcar_extracao": Param(False, type="boolean", description="Baixar de novo o arquivo."),
    },
    default_args={"retries": 3, "retry_delay": timedelta(minutes=5)},
    tags=["cnpj"],
)
def cnpj_empresas():
    @task
    def definir_competencia() -> str:
        from cnpj_pipeline.competencia import resolver
        from cnpj_pipeline.config import Settings

        contexto = get_current_context()
        informada = contexto["params"].get("competencia")
        if not informada and not Settings.from_env().source_url:
            raise ValueError(
                "Com origem local, informe a competência ao disparar a DAG: "
                "o arquivo local não identifica o mês de referência."
            )
        referencia = contexto["dag_run"].logical_date or contexto["dag_run"].run_after
        competencia = resolver(informada, referencia)
        log.info("Competência: %s", competencia)
        return competencia

    @task.sensor(poke_interval=3600, timeout=7 * 24 * 3600, mode="reschedule")
    def aguardar_publicacao(competencia: str) -> bool:
        from cnpj_pipeline.config import Settings
        from cnpj_pipeline.extract import publicada

        disponivel = publicada(Settings.from_env(), competencia)
        log.info("Competência %s publicada na origem: %s", competencia, disponivel)
        return disponivel

    @task
    def extrair_zip(competencia: str) -> dict:
        from cnpj_pipeline.config import Settings
        from cnpj_pipeline.controle import executar_etapa
        from cnpj_pipeline.extract import extrair

        contexto = get_current_context()
        settings = Settings.from_env()
        return executar_etapa(
            settings,
            run_id=contexto["run_id"],
            competencia=competencia,
            etapa="extracao",
            funcao=lambda: extrair(
                competencia, settings, force=bool(contexto["params"].get("forcar_extracao"))
            ),
        )

    @task
    def carregar_bronze(competencia: str, extracao: dict) -> dict:
        from cnpj_pipeline.bronze import carregar_bronze as carga
        from cnpj_pipeline.config import Settings
        from cnpj_pipeline.controle import executar_etapa

        contexto = get_current_context()
        settings = Settings.from_env()
        return executar_etapa(
            settings,
            run_id=contexto["run_id"],
            competencia=competencia,
            etapa="bronze",
            funcao=lambda: carga(competencia, settings, run_id=contexto["run_id"]),
        )

    def _etapa_dbt(nome: str, selecao: str, competencia: str, anterior: dict) -> dict:
        from cnpj_pipeline.config import Settings
        from cnpj_pipeline.controle import executar_etapa

        contexto = get_current_context()
        settings = Settings.from_env()

        def rodar() -> dict:
            _executar_dbt(selecao, competencia)
            return {"linhas_bronze": anterior.get("linhas_bronze")}

        return executar_etapa(
            settings,
            run_id=contexto["run_id"],
            competencia=competencia,
            etapa=nome,
            funcao=rodar,
        )

    @task
    def dbt_silver(competencia: str, bronze: dict) -> dict:
        """Tipagem, limpeza e testes da silver."""
        return _etapa_dbt("dbt_silver", "tag:silver", competencia, bronze)

    @task
    def dbt_gold(competencia: str, silver: dict) -> dict:
        """Seeds, dimensões, fato, marts e testes da gold."""
        return _etapa_dbt("dbt_gold", "tag:gold", competencia, silver)

    competencia = definir_competencia()
    espera = aguardar_publicacao(competencia)
    extracao = extrair_zip(competencia)
    espera >> extracao
    bronze = carregar_bronze(competencia, extracao)
    silver = dbt_silver(competencia, bronze)
    dbt_gold(competencia, silver)


cnpj_empresas()
