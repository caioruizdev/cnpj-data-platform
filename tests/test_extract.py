import hashlib

import pytest

fsspec = pytest.importorskip("fsspec")

from cnpj_pipeline.extract import caminho_zip, extrair  # noqa: E402
from cnpj_pipeline.storage import exists, get_bytes  # noqa: E402


@pytest.fixture
def fs():
    memoria = fsspec.filesystem("memory")
    memoria.store.clear()
    return memoria


def test_extrai_zip_local_e_grava_checksum(fs, settings, conteudo_zip):
    resultado = extrair("2026-10", settings, fs=fs)

    assert resultado["reaproveitado"] is False
    assert resultado["bytes"] == len(conteudo_zip)
    assert resultado["sha256"] == hashlib.sha256(conteudo_zip).hexdigest()
    destino = caminho_zip(settings, "2026-10")
    assert get_bytes(fs, destino) == conteudo_zip
    assert exists(fs, f"{destino}.sha256")


def test_segunda_extracao_reaproveita_o_arquivo(fs, settings):
    extrair("2026-10", settings, fs=fs)
    segunda = extrair("2026-10", settings, fs=fs)
    assert segunda["reaproveitado"] is True


def test_force_baixa_de_novo(fs, settings):
    extrair("2026-10", settings, fs=fs)
    assert extrair("2026-10", settings, fs=fs, force=True)["reaproveitado"] is False


def test_conteudo_que_nao_e_zip_e_rejeitado_e_nao_deixa_resto(fs, settings, tmp_path):
    from dataclasses import replace

    invalido = tmp_path / "invalido.zip"
    invalido.write_bytes(b"isto nao e um zip")
    with pytest.raises(ValueError):
        extrair("2026-10", replace(settings, local_zip_path=str(invalido)), fs=fs)
    assert not exists(fs, caminho_zip(settings, "2026-10"))


def test_origem_local_ausente_gera_erro_claro(fs, settings, tmp_path):
    from dataclasses import replace

    with pytest.raises(FileNotFoundError):
        extrair("2026-10", replace(settings, local_zip_path=str(tmp_path / "nada.zip")), fs=fs)


def test_competencia_invalida_e_rejeitada(fs, settings):
    with pytest.raises(ValueError):
        extrair("2026-13", settings, fs=fs)


def test_zip_armazenado_corrompido_nao_e_reaproveitado(fs, settings):
    from cnpj_pipeline.storage import put_bytes

    extrair("2026-10", settings, fs=fs)
    destino = caminho_zip(settings, "2026-10")
    put_bytes(fs, destino, b"conteudo alterado sem atualizar o sidecar")

    with pytest.raises(ValueError, match="Checksum divergente"):
        extrair("2026-10", settings, fs=fs)


def test_extracao_forcada_com_falha_remove_checksum_antigo(
    fs, settings, tmp_path
):
    from dataclasses import replace

    extrair("2026-10", settings, fs=fs)
    destino = caminho_zip(settings, "2026-10")
    sidecar = f"{destino}.sha256"

    assert exists(fs, sidecar)

    origem_invalida = tmp_path / "origem_invalida.zip"
    origem_invalida.write_bytes(b"arquivo invalido")

    with pytest.raises(ValueError, match="não é um arquivo zip"):
        extrair(
            "2026-10",
            replace(settings, local_zip_path=str(origem_invalida)),
            fs=fs,
            force=True,
        )

    assert not exists(fs, destino)
    assert not exists(fs, sidecar)
