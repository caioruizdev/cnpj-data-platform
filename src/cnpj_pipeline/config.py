"""Configuração lida de variáveis de ambiente (nada fixo no código, nada de segredo no Git)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    storage_backend: str
    azure_connection_string: str
    source_container: str
    # Template da URL de origem; "{competencia}" é substituído por AAAA-MM.
    # Vazio: usa o arquivo local em local_zip_path.
    source_url: str = ""
    local_zip_path: str = "/opt/airflow/data/Empresas0.zip"
    warehouse_path: str = "/opt/airflow/warehouse/cnpj.duckdb"
    tmp_dir: str = "/opt/airflow/warehouse/tmp"
    memory_limit: str = "3GB"
    threads: int = 2
    # Percentual máximo de linhas do arquivo que podem ser descartadas na carga.
    max_rejeitadas_pct: float = 0.1

    @classmethod
    def from_env(cls) -> "Settings":
        backend = os.environ.get("STORAGE_BACKEND", "azurite")
        if backend not in {"azurite", "azure"}:
            raise ValueError(f"STORAGE_BACKEND inválido: {backend!r} (use 'azurite' ou 'azure')")
        conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
        if not conn:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING não definida (veja .env.example)")
        padrao = cls.__dataclass_fields__
        return cls(
            storage_backend=backend,
            azure_connection_string=conn,
            source_container=os.environ.get("SOURCE_CONTAINER", "source-files"),
            source_url=os.environ.get("CNPJ_SOURCE_URL", ""),
            local_zip_path=os.environ.get("CNPJ_LOCAL_ZIP", padrao["local_zip_path"].default),
            warehouse_path=os.environ.get("WAREHOUSE_PATH", padrao["warehouse_path"].default),
            tmp_dir=os.environ.get("TMP_DIR", padrao["tmp_dir"].default),
            memory_limit=os.environ.get("WAREHOUSE_MEMORY_LIMIT", padrao["memory_limit"].default),
            threads=int(os.environ.get("WAREHOUSE_THREADS", padrao["threads"].default)),
            max_rejeitadas_pct=float(
                os.environ.get("MAX_REJEITADAS_PCT", padrao["max_rejeitadas_pct"].default)
            ),
        )
