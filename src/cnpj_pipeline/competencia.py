"""Competência = mês de referência da base (formato AAAA-MM)."""

import re
from datetime import datetime

_PADRAO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validar(competencia: str) -> str:
    if not isinstance(competencia, str) or not _PADRAO.match(competencia):
        raise ValueError(f"Competência inválida: {competencia!r} (esperado AAAA-MM)")
    return competencia


def resolver(parametro: str | None, referencia: datetime) -> str:
    """Usa o parâmetro informado; sem ele, o mês da data de referência da execução."""
    if parametro:
        return validar(parametro.strip())
    return referencia.strftime("%Y-%m")
