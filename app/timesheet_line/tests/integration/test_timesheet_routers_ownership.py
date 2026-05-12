"""Tests de regresión para el ownership check de VT-04 (GEO-1389).

El pentest 2026-04 reportó un IDOR en `PUT /api/v1/timesheet/{id}` (cualquier
usuario podía editar el timesheet de cualquier otro empleado pasando solo el
ID). Durante el fix se descubrió que `DELETE /api/v1/timesheet/` tenía
exactamente el mismo bug (recibe lista de IDs y borraba sin validar dueño).

Estos tests cubren ambos endpoints y bloquean la regresión.
"""

from datetime import date
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.timesheet_line.api.routers import (
    router,
    get_timesheet_gateway,
    get_employee_gateway,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.users.domain.models import Employee
from app.shared.security.dependencies import get_current_user
from app.shared.security.role_enums.dev import Roles


app = FastAPI()
app.include_router(router)


# ----------------------------------------------------------------------
# Helpers de construcción de overrides
# ----------------------------------------------------------------------


def _detailed_timesheet(timesheet_id: int, owner_employee_id: int) -> DetailedTimesheetLine:
    """Construye una `DetailedTimesheetLine` minimal con el dueño indicado."""
    return DetailedTimesheetLine(
        id=timesheet_id,
        name=f"Timesheet {timesheet_id}",
        employee_id=owner_employee_id,
        project=Project(id=10, name="Test Project"),
        task=None,
        hours=4.0,
        date=date(2026, 4, 1),
        validated=False,
    )


def _build_timesheet_gateway(
    *,
    timesheets_by_id: dict[int, DetailedTimesheetLine] | None = None,
    team_member_ids: list[int] | None = None,
    update_result: bool = True,
    delete_result: bool = True,
):
    """Construye un mock de `TimesheetLineGateway` con:
      - `get_by_id` / `get_by_ids` resolviendo los timesheets del dict.
      - `get_team_users` devolviendo los IDs indicados.
      - `update` / `delete` retornando los flags pasados.
    """
    gateway = Mock()
    timesheets_by_id = timesheets_by_id or {}

    def get_by_id(ts_id):
        return timesheets_by_id.get(ts_id)

    def get_by_ids(ts_ids):
        found = [timesheets_by_id[i] for i in ts_ids if i in timesheets_by_id]
        return found

    gateway.get_by_id.side_effect = get_by_id
    gateway.get_by_ids.side_effect = get_by_ids
    gateway.get_team_users.return_value = [
        {"id": uid, "name": f"User {uid}", "work_email": f"u{uid}@example.com"}
        for uid in (team_member_ids or [])
    ]
    gateway.update.return_value = update_result
    gateway.delete.return_value = delete_result
    return gateway


def _build_employee_gateway(requester_employee: Employee | None):
    gateway = Mock()
    gateway.get_by_id.return_value = requester_employee
    return gateway


def _override_user(user_id: int, *, is_approver: bool = False):
    """Construye un override de `get_current_user` con el user_id indicado."""

    async def mock_user():
        return {
            "user_id": user_id,
            "user_email": f"u{user_id}@example.com",
            "user_name": f"User {user_id}",
            "roles": [Roles.approver] if is_approver else [1],
        }

    return mock_user


# ----------------------------------------------------------------------
# Tests para PUT /timesheet/{id}
# ----------------------------------------------------------------------


def _put_body(timesheet_id: int, employee_id: int, *, hours: float = 4.0, validated: bool = False):
    return {
        "id": timesheet_id,
        "name": "Editado",
        "employee_id": employee_id,
        "project_id": 10,
        "hours": hours,
        "date": "2026-04-01",
        "validated": validated,
    }


@pytest.mark.integration
def test_put_timesheet_owner_can_edit_own():
    """Camino feliz: el dueño puede editar su propio timesheet."""
    timesheet = _detailed_timesheet(timesheet_id=100, owner_employee_id=1)
    gateway = _build_timesheet_gateway(timesheets_by_id={100: timesheet})
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            response = client.put("/timesheet/100", json=_put_body(100, 1))
            assert response.status_code == 200
            assert response.json()["success"] is True
            gateway.update.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_put_timesheet_blocks_idor_against_another_employee():
    """VT-04: usuario 1 intenta editar el timesheet del usuario 2 → 403."""
    timesheet = _detailed_timesheet(timesheet_id=100, owner_employee_id=2)
    gateway = _build_timesheet_gateway(
        timesheets_by_id={100: timesheet}, team_member_ids=[]
    )
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            response = client.put("/timesheet/100", json=_put_body(100, 2))
            assert response.status_code == 403
            assert "permisos" in response.json()["detail"].lower()
            gateway.update.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_put_timesheet_approver_can_edit_team_member():
    """Un approver puede editar el timesheet de un miembro de su equipo."""
    timesheet = _detailed_timesheet(timesheet_id=100, owner_employee_id=2)
    gateway = _build_timesheet_gateway(
        timesheets_by_id={100: timesheet}, team_member_ids=[2, 3]
    )
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="approver@example.com", full_name="Approver")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1, is_approver=True)

    try:
        with TestClient(app) as client:
            response = client.put("/timesheet/100", json=_put_body(100, 2))
            assert response.status_code == 200
            gateway.update.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_put_timesheet_approver_blocked_for_employee_outside_team():
    """Approver fuera de scope: aunque tenga rol approver, si el dueño no está
    en su equipo Odoo, debe recibir 403."""
    timesheet = _detailed_timesheet(timesheet_id=100, owner_employee_id=99)
    gateway = _build_timesheet_gateway(
        timesheets_by_id={100: timesheet}, team_member_ids=[2, 3]
    )
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="approver@example.com", full_name="Approver")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1, is_approver=True)

    try:
        with TestClient(app) as client:
            response = client.put("/timesheet/100", json=_put_body(100, 99))
            assert response.status_code == 403
            gateway.update.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_put_timesheet_blocks_employee_id_transfer():
    """VT-04 (vector adicional): aunque el solicitante sea dueño del timesheet,
    no puede cambiar `employee_id` para "transferir" el registro a otro
    empleado.
    """
    timesheet = _detailed_timesheet(timesheet_id=100, owner_employee_id=1)
    gateway = _build_timesheet_gateway(timesheets_by_id={100: timesheet})
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            # body trae employee_id=2 distinto al dueño real (1)
            response = client.put("/timesheet/100", json=_put_body(100, 2))
            assert response.status_code == 403
            assert "empleado" in response.json()["detail"].lower()
            gateway.update.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_put_timesheet_not_found_returns_404():
    """Si el timesheet no existe en Odoo, responder 404 (no 403). No filtramos
    existencia para usuarios autenticados con scope correcto; el 403 se
    reserva para el caso de scope inválido."""
    gateway = _build_timesheet_gateway(timesheets_by_id={})  # no existe
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            response = client.put("/timesheet/100", json=_put_body(100, 1))
            assert response.status_code == 404
            gateway.update.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_put_timesheet_url_id_mismatch_with_body_returns_400():
    """Si el `timesheet_id` de la URL no coincide con `req.id` del body,
    devolver 400 antes de hacer el ownership check (validación de input)."""
    gateway = _build_timesheet_gateway()
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            # URL=100, body.id=200
            response = client.put("/timesheet/100", json=_put_body(200, 1))
            assert response.status_code == 400
            gateway.get_by_id.assert_not_called()
            gateway.update.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_put_timesheet_requester_without_employee_returns_403():
    """Si el solicitante no tiene Employee asociado en Odoo, 403 (fail-closed)."""
    timesheet = _detailed_timesheet(timesheet_id=100, owner_employee_id=1)
    gateway = _build_timesheet_gateway(timesheets_by_id={100: timesheet})
    employee_gateway = _build_employee_gateway(None)

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            response = client.put("/timesheet/100", json=_put_body(100, 1))
            assert response.status_code == 403
            assert "empleado asociado" in response.json()["detail"].lower()
            gateway.update.assert_not_called()
    finally:
        app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# Tests para DELETE /timesheet/ (bonus, mismo IDOR)
# ----------------------------------------------------------------------


@pytest.mark.integration
def test_delete_timesheet_owner_can_delete_own():
    """Camino feliz: el dueño puede borrar sus propios timesheets."""
    ts1 = _detailed_timesheet(100, 1)
    ts2 = _detailed_timesheet(101, 1)
    gateway = _build_timesheet_gateway(timesheets_by_id={100: ts1, 101: ts2})
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            response = client.request("DELETE", "/timesheet/", json={"ids": [100, 101]})
            assert response.status_code == 200
            gateway.delete.assert_called_once_with([100, 101])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_delete_timesheet_blocks_idor_against_another_employee():
    """VT-04 (DELETE): usuario 1 intenta borrar el timesheet del usuario 2 → 403."""
    foreign_ts = _detailed_timesheet(100, owner_employee_id=2)
    gateway = _build_timesheet_gateway(
        timesheets_by_id={100: foreign_ts}, team_member_ids=[]
    )
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            response = client.request("DELETE", "/timesheet/", json={"ids": [100]})
            assert response.status_code == 403
            gateway.delete.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_delete_timesheet_mixed_ids_all_or_nothing():
    """Si en el lote viene 1 propio + 1 ajeno, NADA se borra (todo o nada)."""
    own = _detailed_timesheet(100, owner_employee_id=1)
    foreign = _detailed_timesheet(101, owner_employee_id=2)
    gateway = _build_timesheet_gateway(
        timesheets_by_id={100: own, 101: foreign}, team_member_ids=[]
    )
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            response = client.request("DELETE", "/timesheet/", json={"ids": [100, 101]})
            assert response.status_code == 403
            gateway.delete.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_delete_timesheet_approver_can_delete_team_member():
    """Approver puede borrar timesheets de su equipo."""
    foreign = _detailed_timesheet(100, owner_employee_id=2)
    gateway = _build_timesheet_gateway(
        timesheets_by_id={100: foreign}, team_member_ids=[2, 3]
    )
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="approver@example.com", full_name="Approver")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1, is_approver=True)

    try:
        with TestClient(app) as client:
            response = client.request("DELETE", "/timesheet/", json={"ids": [100]})
            assert response.status_code == 200
            gateway.delete.assert_called_once_with([100])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_delete_timesheet_not_found_returns_404():
    """Si alguno de los IDs no existe en Odoo, 404 antes del ownership check."""
    gateway = _build_timesheet_gateway(timesheets_by_id={})
    employee_gateway = _build_employee_gateway(
        Employee(id=1, email="u1@example.com", full_name="U1")
    )

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_current_user] = _override_user(1)

    try:
        with TestClient(app) as client:
            response = client.request("DELETE", "/timesheet/", json={"ids": [999]})
            assert response.status_code == 404
            gateway.delete.assert_not_called()
    finally:
        app.dependency_overrides.clear()
