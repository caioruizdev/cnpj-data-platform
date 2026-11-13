import fsspec
import pytest

from cnpj_pipeline.config import Settings
from cnpj_pipeline.storage import exists, get_bytes, put_bytes


@pytest.fixture
def fs():
    memory = fsspec.filesystem("memory")
    memory.store.clear()
    return memory


def test_put_get_roundtrip(fs):
    put_bytes(fs, "/source-files/2026-10/arquivo.bin", b"abc")
    assert exists(fs, "/source-files/2026-10/arquivo.bin")
    assert get_bytes(fs, "/source-files/2026-10/arquivo.bin") == b"abc"


def test_exists_false_for_missing_object(fs):
    assert not exists(fs, "/source-files/nao-existe")


def test_settings_requires_connection_string(monkeypatch):
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_settings_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "x")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "x")
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("SOURCE_CONTAINER", raising=False)
    s = Settings.from_env()
    assert s.storage_backend == "azurite"
    assert s.source_container == "source-files"


def test_settings_le_origem_e_warehouse_do_ambiente(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "x")
    monkeypatch.setenv("CNPJ_SOURCE_URL", "https://exemplo/{competencia}/Empresas0.zip")
    monkeypatch.setenv("WAREHOUSE_PATH", "/tmp/w.duckdb")
    monkeypatch.setenv("MAX_REJEITADAS_PCT", "0.5")
    s = Settings.from_env()
    assert s.source_url == "https://exemplo/{competencia}/Empresas0.zip"
    assert s.warehouse_path == "/tmp/w.duckdb"
    assert s.max_rejeitadas_pct == 0.5
