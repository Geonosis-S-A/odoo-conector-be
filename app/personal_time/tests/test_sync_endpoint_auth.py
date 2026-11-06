"""POST /timeoff/sync exige usuario autenticado con rol aprobador."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.personal_time.api import routers as timeoff_routers
from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(timeoff_routers.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: None
    return app


def _user(roles):
    return lambda: {"user_id": 1, "user_email": "x@e.com", "user_name": "X", "roles": roles}


def test_sin_token_es_rechazado():
    resp = TestClient(_app()).post("/api/v1/timeoff/sync")
    assert resp.status_code in (401, 403)


def test_usuario_sin_rol_aprobador_recibe_403():
    app = _app()
    app.dependency_overrides[get_current_user] = _user([])
    resp = TestClient(app).post("/api/v1/timeoff/sync")
    assert resp.status_code == 403


def test_aprobador_pasa_el_chequeo_de_permisos(monkeypatch):
    """Con rol aprobador se llega a ejecutar la sincronización (la cortamos ahí)."""

    class _Stop(Exception):
        pass

    def _boom(db):
        raise _Stop()

    monkeypatch.setattr(timeoff_routers, "SQLModelTimeOffSyncLogRepository", _boom)
    app = _app()
    app.dependency_overrides[get_current_user] = _user([Roles.approver])
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/v1/timeoff/sync")
    # No es 401/403: pasó el guard y falló recién dentro de la sincronización.
    assert resp.status_code not in (401, 403)
