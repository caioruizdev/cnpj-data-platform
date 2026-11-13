"""Carga da camada bronze: o CSV como veio (tudo texto) mais metadados de linhagem.

Nenhuma regra de negócio entra aqui. Tipagem e limpeza são da silver (dbt).
A carga é idempotente: recarregar uma competência apaga e reinsere só aquela competência,
dentro de uma transação.
"""

import hashlib
import logging
import shutil
import zipfile
from pathlib import Path
from uuid import uuid4

import duckdb
import fsspec

from cnpj_pipeline.competencia import validar
from cnpj_pipeline.config import Settings
from cnpj_pipeline.extract import NOME_ARQUIVO, TAMANHO_BLOCO, caminho_zip
from cnpj_pipeline.storage import exists, get_bytes, get_filesystem
from cnpj_pipeline.utf8 import converter_para_utf8
from cnpj_pipeline.warehouse import conectar

log = logging.getLogger(__name__)

COLUNAS = [
    "cnpj_basico",
    "razao_social",
    "natureza_juridica",
    "qualificacao_responsavel",
    "capital_social",
    "porte_empresa",
    "ente_federativo_responsavel",
]

DDL = f"""
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE TABLE IF NOT EXISTS bronze.empresas (
    {", ".join(f"{c} VARCHAR" for c in COLUNAS)},
    _competencia  VARCHAR,
    _arquivo      VARCHAR,
    _sha256       VARCHAR,
    _carregado_em TIMESTAMP,
    _run_id       VARCHAR
);
"""


def _leitura_csv(csv: Path) -> str:
    """Expressão read_csv: sem header, tudo VARCHAR, linhas inválidas ignoradas e contadas."""
    colunas = ", ".join(f"'{c}': 'VARCHAR'" for c in COLUNAS)
    caminho = str(csv).replace("'", "''")
    return (
        f"read_csv('{caminho}', delim=';', quote='\"', escape='\"', header=false, "
        f"columns={{{colunas}}}, ignore_errors=true)"
    )


def _inserir(
    settings: Settings,
    csv: Path,
    competencia: str,
    arquivo: str,
    sha256: str,
    run_id: str,
    linhas_arquivo: int,
) -> int:
    con = conectar(settings)
    try:
        con.execute(DDL)
        con.execute("BEGIN")
        try:
            con.execute("DELETE FROM bronze.empresas WHERE _competencia = ?", [competencia])
            con.execute(
                f"""
                INSERT INTO bronze.empresas
                SELECT *, CAST(? AS VARCHAR), CAST(? AS VARCHAR), CAST(? AS VARCHAR),
                       CAST(now() AS TIMESTAMP), CAST(? AS VARCHAR)
                FROM {_leitura_csv(csv)}
                """,
                [competencia, arquivo, sha256, run_id],
            )
            linhas_bronze = con.execute(
                "SELECT count(*) FROM bronze.empresas WHERE _competencia = ?", [competencia]
            ).fetchone()[0]

            rejeitadas = linhas_arquivo - linhas_bronze
            limite = linhas_arquivo * settings.max_rejeitadas_pct / 100
            if rejeitadas < 0 or rejeitadas > limite:
                raise ValueError(
                    f"Reconciliação falhou: arquivo={linhas_arquivo} linhas, "
                    f"bronze={linhas_bronze}, rejeitadas={rejeitadas} "
                    f"(limite {settings.max_rejeitadas_pct}%)."
                )
            con.execute("COMMIT")
        except Exception:
            try:
                con.execute("ROLLBACK")
            except duckdb.Error:
                pass
            raise
        return linhas_bronze
    finally:
        con.close()


def carregar_bronze(
    competencia: str,
    settings: Settings,
    fs: fsspec.AbstractFileSystem | None = None,
    run_id: str = "manual",
) -> dict:
    validar(competencia)
    fs = fs or get_filesystem(settings)
    blob = caminho_zip(settings, competencia)
    if not exists(fs, blob):
        raise FileNotFoundError(f"Arquivo da competência {competencia} não encontrado: {blob}")
    sha256 = get_bytes(fs, f"{blob}.sha256").decode().split()[0]

    trabalho = Path(settings.tmp_dir) / f"bronze_{competencia}_{uuid4().hex[:8]}"
    trabalho.mkdir(parents=True, exist_ok=True)
    try:
        zip_local = trabalho / NOME_ARQUIVO
        hash_ = hashlib.sha256()
        with fs.open(blob, "rb") as origem, open(zip_local, "wb") as destino:
            while bloco := origem.read(TAMANHO_BLOCO):
                hash_.update(bloco)
                destino.write(bloco)
        if hash_.hexdigest() != sha256:
            raise ValueError(
                f"Checksum divergente para a competencia {competencia}: "
                "o arquivo do storage nao corresponde ao manifesto .sha256."
            )

        csv_utf8 = trabalho / "empresas.csv"
        with zipfile.ZipFile(zip_local) as zf:
            membros = [m for m in zf.infolist() if not m.is_dir()]
            if len(membros) != 1:
                raise ValueError(f"Esperado 1 arquivo dentro do zip, encontrado {len(membros)}.")
            arquivo = membros[0].filename
            with zf.open(membros[0]) as conteudo:
                linhas_arquivo = converter_para_utf8(conteudo, csv_utf8)
        log.info("%s: %s linhas no arquivo", arquivo, linhas_arquivo)

        linhas_bronze = _inserir(
            settings, csv_utf8, competencia, arquivo, sha256, run_id, linhas_arquivo
        )
    finally:
        shutil.rmtree(trabalho, ignore_errors=True)

    log.info("Bronze carregada: %s linhas (competência %s)", linhas_bronze, competencia)
    return {
        "arquivo": arquivo,
        "sha256": sha256,
        "linhas_arquivo": linhas_arquivo,
        "linhas_bronze": linhas_bronze,
        "linhas_rejeitadas": linhas_arquivo - linhas_bronze,
    }
