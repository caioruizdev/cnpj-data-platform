"""Conexão com o warehouse local (DuckDB)."""

from pathlib import Path

import duckdb

from cnpj_pipeline.config import Settings


def conectar(settings: Settings, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    caminho = Path(settings.warehouse_path)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(caminho), read_only=read_only)
    con.execute(f"SET memory_limit = '{settings.memory_limit}'")
    con.execute(f"SET threads = {int(settings.threads)}")
    spill = Path(settings.tmp_dir) / "duckdb_spill"
    spill.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory = '{spill}'")
    # Reduz o consumo de memória em cargas grandes (a ordem das linhas não importa aqui).
    con.execute("SET preserve_insertion_order = false")
    return con
