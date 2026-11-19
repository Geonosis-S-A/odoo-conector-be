"""POST /timesheet/: solo se cargan horas a nombre propio.

Todo mockeado (sin Odoo ni DB reales): el ``employee_id`` de cada línea debe ser
el del usuario autenticado; si no, 403 y no se crea nada.
"""
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.project.domain.models import Project
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles
from app.timesheet_line.api.routers import (
    get_employee_gateway,
    get_project_assignment_gateway,
    get_timesheet_gateway,
    router,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine

ME = 10
OTHER = 20
PROJECT = 1


def _line(employee_id: int, project_id: int = PROJECT) -> dict:
    return {
        "name": "x",
        "employee_id": employee_id,
        "project_id": project_id,
        "hours": 1.0,
        "date": "2025-01-06",
    }


@pytest.fixture
def gateway():
    gw = MagicMock()
    gw.create.return_value = [7]
    gw.get_by_ids.return_value = [
        DetailedTimesheetLine(
            id=7,
            name="x",
            employee_id=ME,
            project=Project(id=PROJECT, name="p"),
            task=None,
            hours=1.0,
            date=date(2025, 1, 6),
            validated=False,
        )
    ]
    return gw


@pytest.fixture
def assignments():
    gw = MagicMock()
    gw.is_employee_assigned.return_value = True
    return gw


def _client(gateway, assignments, roles) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def _user():
        return {
            "user_id": ME,
            "user_email": "me@example.com",
            "user_name": "Yo",
            "roles": roles,
        }

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_project_assignment_gateway] = lambda: assignments
    app.dependency_overrides[get_employee_gateway] = lambda: MagicMock()
    return TestClient(app)


def test_post_con_employee_id_propio_crea_las_horas(gateway, assignments):
    client = _client(gateway, assignments, roles=[])

    r = client.post("/api/v1/timesheet/", json=[_line(ME)])

    assert r.status_code == 200
    gateway.create.assert_called_once()


def test_post_con_employee_id_ajeno_es_403_y_no_crea(gateway, assignments):
    client = _client(gateway, assignments, roles=[])

    r = client.post("/api/v1/timesheet/", json=[_line(OTHER)])

    assert r.status_code == 403
    gateway.create.assert_not_called()


def test_post_lote_con_una_linea_ajena_se_rechaza_completo(gateway, assignments):
    client = _client(gateway, assignments, roles=[])

    r = client.post("/api/v1/timesheet/", json=[_line(ME), _line(OTHER)])

    assert r.status_code == 403
    gateway.create.assert_not_called()


def test_post_ajeno_tampoco_lo_permite_un_aprobador(gateway, assignments):
    client = _client(gateway, assignments, roles=[Roles.approver])

    r = client.post("/api/v1/timesheet/", json=[_line(OTHER)])

    assert r.status_code == 403
    gateway.create.assert_not_called()
