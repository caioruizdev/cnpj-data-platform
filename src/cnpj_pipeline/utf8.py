"""Conversão do CSV da Receita (ISO-8859-1) para UTF-8, em blocos e com contagem de linhas."""

from pathlib import Path
from typing import BinaryIO

TAMANHO_BLOCO = 16 * 1024 * 1024


def converter_para_utf8(origem: BinaryIO, destino: Path, tamanho_bloco: int = TAMANHO_BLOCO) -> int:
    """Lê `origem` (latin-1), grava `destino` (UTF-8) e devolve o número de linhas.

    Latin-1 é um encoding de um byte por caractere: decodificar por blocos é seguro,
    sem risco de cortar um caractere no meio. A memória usada é de um bloco por vez.
    """
    linhas = 0
    ultimo_byte = b"\n"
    with open(destino, "wb") as saida:
        while bloco := origem.read(tamanho_bloco):
            linhas += bloco.count(b"\n")
            ultimo_byte = bloco[-1:]
            saida.write(bloco.decode("latin-1").encode("utf-8"))
    if ultimo_byte != b"\n":
        linhas += 1
    return linhas
