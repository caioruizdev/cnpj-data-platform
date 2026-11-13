import io
import zipfile

import pytest

from cnpj_pipeline.config import Settings

LINHAS = [
    '"11111111";"EMPRESA TESTE LTDA";"2062";"49";"1000,00";"03";""',
    '"22222222";"FULANO DE TAL 12345678901";"2135";"50";"5000,00";"01";""',
    '"33333333";"AÇÚCAR & CIA";"2062";"49";"";"05";""',
    '"44444444";"44.444.444 BELTRANO DA SILVA";"2135";"50";"0,00";"00";""',
]


@pytest.fixture
def conteudo_zip() -> bytes:
    """Zip com um CSV em latin-1, como a Receita publica."""
    texto = "\n".join(LINHAS) + "\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("K3241.K03200Y0.D61010.EMPRECSV", texto.encode("latin-1"))
    return buffer.getvalue()


@pytest.fixture
def settings(tmp_path, conteudo_zip) -> Settings:
    origem = tmp_path / "Empresas0.zip"
    origem.write_bytes(conteudo_zip)
    return Settings(
        storage_backend="azurite",
        azure_connection_string="x",
        source_container="source-files",
        source_url="",
        local_zip_path=str(origem),
        warehouse_path=str(tmp_path / "warehouse" / "cnpj.duckdb"),
        tmp_dir=str(tmp_path / "tmp"),
        memory_limit="1GB",
        max_rejeitadas_pct=0.0,
    )
