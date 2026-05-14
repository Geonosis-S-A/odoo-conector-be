"""VT-15 (GEO-1391): regresión HPP en ``employee_id`` para listado de timesheets."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.security.dependencies import get_current_user
from app.timesheet_line.api.routers import (
    router,
    get_timesheet_gateway,
    get_employee_gateway,
    get_task_gateway,
    get_notification_repository,
)


@pytest.fixture
def list_hpp_app():
    """App mínima con router timesheet y dependencias mockeadas para GET /timesheet/."""
    app = FastAPI()
    app.include_router(router)

    gw = Mock()
    gw.count.return_value = 0
    gw.all.return_value = []

    eg = Mock()
    eg.exists_by_id.return_value = True
    eg.all.return_value = []

    tg = Mock()
    nr = Mock()
    nr.get_by_timesheet_ids.return_value = []

    async def current_plain():
        return {
            "user_id": 10,
            "user_email": "u10@example.com",
            "user_name": "U10",
            "roles": [1],
        }

    app.dependency_overrides[get_timesheet_gateway] = lambda: gw
    app.dependency_overrides[get_employee_gateway] = lambda: eg
    app.dependency_overrides[get_task_gateway] = lambda: tg
    app.dependency_overrides[get_notification_repository] = lambda: nr
    app.dependency_overrides[get_current_user] = current_plain

    yield app

    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "qs_suffix",
    [
        "employee_id%5B%5D=615",
        "employee_id%5B0%5D=615",
    ],
)
def test_get_timesheet_rejects_bracket_notation_vt15(list_hpp_app, qs_suffix):
    client = TestClient(list_hpp_app)
    r = client.get(
        f"/timesheet/?{qs_suffix}&date_from=2026-01-01&date_to=2026-01-31&page=1&page_size=10"
    )
    assert r.status_code == 400
    detail = r.json()["detail"].lower()
    assert "employee_id[]" in detail or "notación" in detail


def test_get_timesheet_rejects_duplicate_employee_id(list_hpp_app):
    client = TestClient(list_hpp_app)
    r = client.get(
        "/timesheet/?employee_id=1&employee_id=2&date_from=2026-01-01&date_to=2026-01-31&page=1&page_size=10"
    )
    assert r.status_code == 400
    assert "duplicado" in r.json()["detail"]


def test_get_timesheet_ok_scalar_employee_id_same_user(list_hpp_app):
    client = TestClient(list_hpp_app)
    r = client.get(
        "/timesheet/?employee_id=10&date_from=2026-01-01&date_to=2026-01-31&page=1&page_size=10"
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["items"] == []
