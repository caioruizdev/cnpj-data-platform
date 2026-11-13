from datetime import datetime

import pytest

from cnpj_pipeline.competencia import resolver, validar


@pytest.mark.parametrize("valor", ["2026-10", "2025-01", "2026-12"])
def test_validar_aceita_formato_correto(valor):
    assert validar(valor) == valor


@pytest.mark.parametrize("valor", ["2026-13", "2026-00", "202610", "2026-1", "", "abc", None])
def test_validar_rejeita_formato_incorreto(valor):
    with pytest.raises(ValueError):
        validar(valor)


def test_resolver_prefere_o_parametro():
    assert resolver("2026-09", datetime(2026, 11, 12)) == "2026-09"


def test_resolver_usa_mes_da_referencia_sem_parametro():
    assert resolver(None, datetime(2026, 11, 12)) == "2026-11"
    assert resolver("", datetime(2026, 11, 12)) == "2026-11"
