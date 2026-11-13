"""Camada de storage.

Usa fsspec: o mesmo código fala com o Azurite (local) e com o Azure Blob real,
mudando só a connection string. As funções recebem o filesystem como parâmetro
para poderem ser testadas com um filesystem em memória (sem Docker).
"""

import fsspec

from cnpj_pipeline.config import Settings


def get_filesystem(settings: Settings) -> fsspec.AbstractFileSystem:
    """Filesystem 'abfs' (Azure Blob). Azurite e Azure real usam o mesmo protocolo."""
    return fsspec.filesystem("abfs", connection_string=settings.azure_connection_string)


def ensure_container(fs: fsspec.AbstractFileSystem, container: str) -> None:
    if not fs.exists(container):
        fs.mkdir(container)


def put_bytes(fs: fsspec.AbstractFileSystem, path: str, data: bytes) -> None:
    with fs.open(path, "wb") as f:
        f.write(data)


def get_bytes(fs: fsspec.AbstractFileSystem, path: str) -> bytes:
    with fs.open(path, "rb") as f:
        return f.read()


def exists(fs: fsspec.AbstractFileSystem, path: str) -> bool:
    return fs.exists(path)
