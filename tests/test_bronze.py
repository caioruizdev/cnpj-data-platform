import pytest

fsspec = pytest.importorskip("fsspec")
duckdb = pytest.importorskip("duckdb")

from cnpj_pipeline.bronze import carregar_bronze  # noqa: E402
from cnpj_pipeline.extract import extrair  # noqa: E402


@pytest.fixture
def fs():
    memoria = fsspec.filesystem("memory")
    memoria.store.clear()
    return memoria


def _consulta(settings, sql, *parametros):
    con = duckdb.connect(settings.warehouse_path, read_only=True)
    try:
        return con.execute(sql, list(parametros)).fetchall()
    finally:
        con.close()


def test_carrega_todas_as_linhas_com_metadados(fs, settings):
    extracao = extrair("2026-10", settings, fs=fs)
    resultado = carregar_bronze("2026-10", settings, fs=fs, run_id="teste")

    assert resultado["linhas_arquivo"] == 4
    assert resultado["linhas_bronze"] == 4
    assert resultado["linhas_rejeitadas"] == 0
    linhas = _consulta(
        settings,
        "select _competencia, _arquivo, _sha256, _run_id from bronze.empresas limit 1",
    )
    assert linhas == [
        ("2026-10", "K3241.K03200Y0.D61010.EMPRECSV", extracao["sha256"], "teste")
    ]


def test_acentos_sobrevivem_a_conversao_de_encoding(fs, settings):
    extrair("2026-10", settings, fs=fs)
    carregar_bronze("2026-10", settings, fs=fs)
    razao = _consulta(
        settings, "select razao_social from bronze.empresas where cnpj_basico = '33333333'"
    )
    assert razao == [("AÇÚCAR & CIA",)]


def test_bronze_guarda_texto_sem_tratamento(fs, settings):
    extrair("2026-10", settings, fs=fs)
    carregar_bronze("2026-10", settings, fs=fs)
    capital = _consulta(
        settings, "select capital_social from bronze.empresas where cnpj_basico = '22222222'"
    )
    assert capital == [("5000,00",)]


def test_recarregar_a_mesma_competencia_nao_duplica(fs, settings):
    extrair("2026-10", settings, fs=fs)
    carregar_bronze("2026-10", settings, fs=fs)
    carregar_bronze("2026-10", settings, fs=fs)
    assert _consulta(settings, "select count(*) from bronze.empresas") == [(4,)]


def test_competencias_diferentes_convivem_na_bronze(fs, settings):
    extrair("2026-10", settings, fs=fs)
    extrair("2026-11", settings, fs=fs)
    carregar_bronze("2026-10", settings, fs=fs)
    carregar_bronze("2026-11", settings, fs=fs)
    assert _consulta(settings, "select count(*) from bronze.empresas") == [(8,)]
    carregar_bronze("2026-10", settings, fs=fs)
    assert _consulta(settings, "select count(*) from bronze.empresas") == [(8,)]


def test_carga_sem_extracao_previa_falha_com_erro_claro(fs, settings):
    with pytest.raises(FileNotFoundError):
        carregar_bronze("2026-10", settings, fs=fs)


def test_bronze_rejeita_zip_corrompido_sem_alterar_carga_existente(fs, settings):
    from cnpj_pipeline.extract import caminho_zip
    from cnpj_pipeline.storage import put_bytes

    extrair("2026-10", settings, fs=fs)
    carregar_bronze("2026-10", settings, fs=fs)
    antes = _consulta(settings, "select cnpj_basico from bronze.empresas order by cnpj_basico")

    put_bytes(fs, caminho_zip(settings, "2026-10"), b"zip corrompido")
    with pytest.raises(ValueError, match="Checksum divergente"):
        carregar_bronze("2026-10", settings, fs=fs)
    depois = _consulta(settings, "select cnpj_basico from bronze.empresas order by cnpj_basico")
    assert depois == antes


def test_rollback_apos_delete_preserva_competencia(fs, settings, monkeypatch):
    import cnpj_pipeline.bronze as modulo_bronze

    extrair("2026-10", settings, fs=fs)
    carregar_bronze("2026-10", settings, fs=fs)
    antes = _consulta(
        settings, "select cnpj_basico, razao_social from bronze.empresas order by cnpj_basico"
    )

    # O erro ocorre na instrucao INSERT, depois do DELETE e antes do COMMIT.
    monkeypatch.setattr(
        modulo_bronze,
        "_leitura_csv",
        lambda _csv: "read_csv('/arquivo/que/nao/existe.csv')",
    )
    with pytest.raises(duckdb.Error):
        carregar_bronze("2026-10", settings, fs=fs)

    depois = _consulta(
        settings, "select cnpj_basico, razao_social from bronze.empresas order by cnpj_basico"
    )
    assert depois == antes
