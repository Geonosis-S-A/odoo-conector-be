from unittest.mock import patch

import pytest

from agent.services import feriados_service as fs

API = [{"fecha": "2026-05-25", "tipo": "inamovible", "nombre": "Revolución de Mayo"}]


def test_extra_parsea_y_filtra_por_año(monkeypatch):
    monkeypatch.setenv(
        "FERIADOS_EXTRA", "2026-11-10=Día de la Tradición;2027-01-02=Otro;basura;;x=y"
    )
    assert fs.get_feriados_extra(2026) == [
        {"fecha": "2026-11-10", "tipo": "extra", "nombre": "Día de la Tradición"}
    ]


def test_extra_vacio(monkeypatch):
    monkeypatch.delenv("FERIADOS_EXTRA", raising=False)
    assert fs.get_feriados_extra(2026) == []


def test_extra_sin_nombre(monkeypatch):
    monkeypatch.setenv("FERIADOS_EXTRA", "2026-11-10")
    assert fs.get_feriados_extra(2026)[0]["nombre"] == "Feriado"


def test_se_suma_a_la_api(monkeypatch):
    monkeypatch.setenv("FERIADOS_EXTRA", "2026-11-10=Tradición")
    with patch.object(fs, "_get_feriados_api", return_value=list(API)):
        fechas = {f["fecha"] for f in fs.get_feriados_by_year(2026)}
    assert fechas == {"2026-05-25", "2026-11-10"}


def test_check_fechas_detecta_extra(monkeypatch):
    monkeypatch.setenv("FERIADOS_EXTRA", "2026-11-10=Tradición")
    with patch.object(fs, "_get_feriados_api", return_value=list(API)):
        res = fs.check_fechas_feriadas(["2026-11-10", "2026-11-11"])
    assert res == [{"fecha": "2026-11-10", "nombre": "Tradición"}]


def test_extra_funciona_si_la_api_falla(monkeypatch):
    monkeypatch.setenv("FERIADOS_EXTRA", "2026-11-10=Tradición")
    with patch.object(fs, "_get_feriados_api", side_effect=RuntimeError("caída")):
        res = fs.check_fechas_feriadas(["2026-11-10"])
    assert len(res) == 1


def test_sin_extra_y_api_caida_propaga_error(monkeypatch):
    monkeypatch.delenv("FERIADOS_EXTRA", raising=False)
    with patch.object(fs, "_get_feriados_api", side_effect=RuntimeError("caída")):
        with pytest.raises(RuntimeError):
            fs.get_feriados_by_year(2026)
