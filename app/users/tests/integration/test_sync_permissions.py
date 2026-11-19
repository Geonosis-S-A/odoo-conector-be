"""Permisos de POST /users/sync/{employee_id}: el propio usuario o un aprobador."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles
from app.users.api import routers as users_routers


class _FakeUseCase:
    def __init__(self, *args, **kwargs):
        pass

    def execute(self, employee_id):
        return {
            "success": True,
            "message": "ok",
            "user_updated": False,
            "current_data": None,
            "changes_made": None,
        }


def _client(monkeypatch, user_id: int, roles: list[int]) -> TestClient:
    monkeypatch.setattr(users_routers, "get_odoo_connection", lambda: object())
    monkeypatch.setattr(users_routers, "OdooEmployeeGateway", lambda c: object())
    monkeypatch.setattr(users_routers, "SQLModelUserRepository", lambda db: object())
    monkeypatch.setattr(users_routers, "SyncSingleUserChangesUseCase", _FakeUseCase)

    app = FastAPI()
    app.include_router(users_routers.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": user_id,
        "user_email": "x@example.com",
        "user_name": "X",
        "roles": roles,
    }
    return TestClient(app)


def test_usuario_normal_puede_sincronizarse_a_si_mismo(monkeypatch):
    client = _client(monkeypatch, user_id=7, roles=[])
    assert client.post("/api/v1/users/sync/7").status_code == 200


def test_usuario_normal_no_puede_sincronizar_a_otro(monkeypatch):
    client = _client(monkeypatch, user_id=7, roles=[])
    resp = client.post("/api/v1/users/sync/8")
    assert resp.status_code == 403
    # El front lee `message`; FastAPI estándar usa `detail`: van los dos.
    assert resp.json()["message"]
    assert resp.json()["detail"]


def test_aprobador_puede_sincronizar_a_otro(monkeypatch):
    client = _client(monkeypatch, user_id=7, roles=[Roles.approver])
    assert client.post("/api/v1/users/sync/8").status_code == 200
