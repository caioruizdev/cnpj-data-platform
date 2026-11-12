# Imagem oficial do Airflow com as bibliotecas do pipeline e o dbt.
# Versão do Airflow fixada por ARG: reprodutibilidade (sem "latest").
ARG AIRFLOW_VERSION=3.0.6
FROM apache/airflow:${AIRFLOW_VERSION}

COPY docker/airflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# O dbt fica em um virtualenv separado, para não gerar conflito de dependências com o Airflow.
# O DuckDB tem a mesma versão nos dois ambientes (o arquivo do banco é compartilhado).
USER root
RUN mkdir -p /opt/airflow/warehouse \
    && chown -R airflow /opt/airflow/warehouse \
    && python -m venv /opt/dbt-venv \
    && /opt/dbt-venv/bin/pip install --no-cache-dir "duckdb==1.3.2" "dbt-core==1.12.7" "dbt-duckdb==1.11.1" \
    && chown -R airflow /opt/dbt-venv
USER airflow
