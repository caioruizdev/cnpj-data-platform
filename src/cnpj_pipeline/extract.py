"""Extração: leva o Empresas0.zip da origem (URL oficial ou arquivo local) para o storage.

O zip é guardado como veio, com o checksum SHA-256 ao lado. O arquivo `.sha256` é gravado
por último: se ele existe, o download anterior terminou por completo.
"""

import hashlib
import logging
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

import fsspec
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cnpj_pipeline.competencia import validar
from cnpj_pipeline.config import Settings
from cnpj_pipeline.storage import ensure_container, exists, get_bytes, get_filesystem, put_bytes

log = logging.getLogger(__name__)

NOME_ARQUIVO = "Empresas0.zip"
TAMANHO_BLOCO = 8 * 1024 * 1024
ASSINATURA_ZIP = b"PK\x03\x04"


@dataclass
class ResultadoExtracao:
    blob: str
    sha256: str
    bytes: int
    origem: str
    reaproveitado: bool

    def como_dict(self) -> dict:
        return asdict(self)


def caminho_zip(settings: Settings, competencia: str) -> str:
    return f"{settings.source_container}/cnpj/competencia={competencia}/{NOME_ARQUIVO}"


def url_da_competencia(settings: Settings, competencia: str) -> str:
    return settings.source_url.replace("{competencia}", competencia)


def _sessao() -> requests.Session:
    sessao = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    )
    sessao.mount("https://", HTTPAdapter(max_retries=retry))
    sessao.mount("http://", HTTPAdapter(max_retries=retry))
    sessao.headers["User-Agent"] = "cnpj-pipeline/0.1"
    return sessao


def publicada(settings: Settings, competencia: str) -> bool:
    """A competência já está disponível na origem? Sem URL configurada, considera que sim."""
    if not settings.source_url:
        return True
    url = url_da_competencia(settings, competencia)
    with _sessao() as sessao:
        resposta = sessao.head(url, allow_redirects=True, timeout=30)
        if resposta.status_code in (405, 501):  # servidor sem suporte a HEAD
            resposta = sessao.get(url, stream=True, timeout=30)
            resposta.close()
        if resposta.status_code in (403, 404):
            return False
        resposta.raise_for_status()
    return True


def _baixar(url: str) -> Iterator[bytes]:
    with _sessao() as sessao, sessao.get(url, stream=True, timeout=(30, 120)) as resposta:
        resposta.raise_for_status()
        yield from resposta.iter_content(chunk_size=TAMANHO_BLOCO)


def _ler_local(caminho: str) -> Iterator[bytes]:
    with open(caminho, "rb") as arquivo:
        while bloco := arquivo.read(TAMANHO_BLOCO):
            yield bloco


def _origem(settings: Settings, competencia: str) -> tuple[str, Iterator[bytes]]:
    if settings.source_url:
        url = url_da_competencia(settings, competencia)
        return url, _baixar(url)
    if not Path(settings.local_zip_path).is_file():
        raise FileNotFoundError(
            f"CNPJ_SOURCE_URL não definida e arquivo local ausente: {settings.local_zip_path}"
        )
    return settings.local_zip_path, _ler_local(settings.local_zip_path)


def extrair(
    competencia: str,
    settings: Settings,
    fs: fsspec.AbstractFileSystem | None = None,
    force: bool = False,
) -> dict:
    validar(competencia)
    fs = fs or get_filesystem(settings)
    ensure_container(fs, settings.source_container)

    destino = caminho_zip(settings, competencia)
    sidecar = f"{destino}.sha256"

    if not force and exists(fs, destino) and exists(fs, sidecar):
        sha = get_bytes(fs, sidecar).decode().split()[0]
        # O sidecar comprova uma extracao concluida, mas nao a integridade atual do blob.
        hash_atual = hashlib.sha256()
        with fs.open(destino, "rb") as arquivo:
            while bloco := arquivo.read(TAMANHO_BLOCO):
                hash_atual.update(bloco)
        if hash_atual.hexdigest() != sha:
            raise ValueError(
                f"Checksum divergente no storage para {destino}: "
                "arquivo armazenado corrompido; reextraia com force=True."
            )
        log.info("Competência %s já extraída (sha256 %s). Reaproveitando.", competencia, sha)
        return ResultadoExtracao(destino, sha, fs.size(destino), "storage", True).como_dict()

    descricao, blocos = _origem(settings, competencia)
    # Invalida o checksum anterior antes de substituir o arquivo.
    if exists(fs, sidecar):
        fs.rm(sidecar)

    log.info("Extraindo %s -> %s", descricao, destino)

    hash_ = hashlib.sha256()
    total = 0
    try:
        with fs.open(destino, "wb") as saida:
            for bloco in blocos:
                if total == 0 and not bloco.startswith(ASSINATURA_ZIP):
                    raise ValueError("O conteúdo recebido não é um arquivo zip.")
                hash_.update(bloco)
                saida.write(bloco)
                total += len(bloco)
        if total == 0:
            raise ValueError("A origem devolveu um arquivo vazio.")
    except Exception:
        try:
            fs.rm(destino)
        except Exception:  # noqa: BLE001 - limpeza de melhor esforço
            log.warning("Não foi possível remover o arquivo parcial %s", destino)
        raise

    sha = hash_.hexdigest()
    put_bytes(fs, sidecar, f"{sha}  {NOME_ARQUIVO}\n".encode())
    log.info("Extração concluída: %s bytes, sha256 %s", total, sha)
    return ResultadoExtracao(destino, sha, total, descricao, False).como_dict()
