from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.feriados.api.routers import router
from app.shared.security.dependencies import get_current_user

API = [{"fecha": "2026-05-25", "tipo": "inamovible", "nombre": "Revolución de Mayo"}]


def _client(auth=True):
    app = FastAPI()
    app.include_router(router)
    if auth:
        app.dependency_overrides[get_current_user] = lambda: object()
    return TestClient(app)


def test_devuelve_api_mas_extra_ordenado(monkeypatch):
    monkeypatch.setenv("FERIADOS_EXTRA", "2026-11-10=Día de la Tradición")
    with patch("agent.services.feriados_service._get_feriados_api", return_value=list(API)):
        r = _client().get("/feriados", params={"year": 2026})
    assert r.status_code == 200
    assert [f["fecha"] for f in r.json()] == ["2026-05-25", "2026-11-10"]


def test_year_obligatorio():
    assert _client().get("/feriados").status_code == 422


def test_api_caida_sin_extra_da_502(monkeypatch):
    monkeypatch.delenv("FERIADOS_EXTRA", raising=False)
    with patch(
        "agent.services.feriados_service._get_feriados_api",
        side_effect=RuntimeError("caída"),
    ):
        assert _client().get("/feriados", params={"year": 2026}).status_code == 502


def test_requiere_autenticacion():
    assert _client(auth=False).get("/feriados", params={"year": 2026}).status_code in (401, 403)
