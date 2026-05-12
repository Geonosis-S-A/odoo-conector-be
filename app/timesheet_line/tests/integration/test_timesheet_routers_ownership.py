"""Tests de regresión de los ownership/scope checks en `/timesheet`.

Cubre:
- VT-04 (GEO-1389): IDOR en `PUT /timesheet/{id}` y `DELETE /timesheet/`.
- VT-14 (GEO-1392): BFLA en `POST /timesheet/validate` + bonus
  `POST /timesheet/review` (mismo patrón: scope + anti-spoofing del
  `approver_mail`).
"""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.timesheet_line.api.routers import (
    router,
    get_timesheet_gateway,
    get_employee_gateway,
)
from app.email.api.dependencies import get_common_email_service
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


def _override_user(
    user_id: int,
    *,
    is_approver: bool = False,
    user_email: str | None = None,
):
    """Construye un override de `get_current_user` con el user_id indicado."""

    async def mock_user():
        return {
            "user_id": user_id,
            "user_email": user_email or f"u{user_id}@example.com",
            "user_name": f"User {user_id}",
            "roles": [Roles.approver] if is_approver else [1],
        }

    return mock_user


def _build_email_service_mock():
    """Mock minimal del `CommonResendEmailService` para los tests de validate
    / review: los métodos enviados son async, así que usamos AsyncMock."""
    service = Mock()
    service.send_approved_mail = AsyncMock(return_value=True)
    service.send_review_mail = AsyncMock(return_value=True)
    return service


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


# ----------------------------------------------------------------------
# Tests para POST /timesheet/validate (VT-14)
# ----------------------------------------------------------------------


def _setup_validate(
    *,
    timesheets: dict[int, DetailedTimesheetLine],
    requester_employee: Employee | None,
    team_member_ids: list[int],
    user_id: int = 1,
    user_email: str = "approver@example.com",
    is_approver: bool = True,
):
    """Wiring común para los tests de validate/review: arma los overrides y
    devuelve los mocks principales para hacer aserciones."""
    gateway = _build_timesheet_gateway(
        timesheets_by_id=timesheets, team_member_ids=team_member_ids
    )
    # `validate` use case llama también a `get_by_email` y `get_by_id` del
    # employee_gateway; el primero resuelve el approver y debe existir.
    employee_gateway = _build_employee_gateway(requester_employee)
    employee_gateway.get_by_email.return_value = requester_employee
    email_service = _build_email_service_mock()

    app.dependency_overrides[get_timesheet_gateway] = lambda: gateway
    app.dependency_overrides[get_employee_gateway] = lambda: employee_gateway
    app.dependency_overrides[get_common_email_service] = lambda: email_service
    app.dependency_overrides[get_current_user] = _override_user(
        user_id, is_approver=is_approver, user_email=user_email
    )
    return gateway, employee_gateway, email_service


@pytest.mark.integration
def test_validate_approver_can_validate_team_members_timesheet():
    """Camino feliz: approver valida timesheets de su equipo con su propio
    email en `approver_mail`."""
    ts = _detailed_timesheet(100, owner_employee_id=2)
    gateway, _, _ = _setup_validate(
        timesheets={100: ts},
        requester_employee=Employee(id=1, email="approver@example.com", full_name="Approver"),
        team_member_ids=[2, 3],
    )
    gateway.validate.return_value = True

    try:
        with TestClient(app) as client:
            response = client.post(
                "/timesheet/validate",
                json={"approver_mail": "approver@example.com", "timesheetline_ids": [100]},
            )
            assert response.status_code == 200
            assert response.json()["success"] is True
            gateway.validate.assert_called_once_with([100])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_non_approver_blocked():
    """Sin rol approver → 403 antes de cualquier otra cosa."""
    ts = _detailed_timesheet(100, owner_employee_id=2)
    gateway, _, _ = _setup_validate(
        timesheets={100: ts},
        requester_employee=Employee(id=1, email="user@example.com", full_name="User"),
        team_member_ids=[],
        user_email="user@example.com",
        is_approver=False,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/timesheet/validate",
                json={"approver_mail": "user@example.com", "timesheetline_ids": [100]},
            )
            assert response.status_code == 403
            gateway.validate.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_blocks_idor_against_other_team():
    """VT-14: approver intenta validar timesheet de empleado fuera de su
    equipo → 403."""
    ts = _detailed_timesheet(100, owner_employee_id=99)
    gateway, _, _ = _setup_validate(
        timesheets={100: ts},
        requester_employee=Employee(id=1, email="approver@example.com", full_name="Approver"),
        team_member_ids=[2, 3],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/timesheet/validate",
                json={"approver_mail": "approver@example.com", "timesheetline_ids": [100]},
            )
            assert response.status_code == 403
            gateway.validate.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_blocks_approver_mail_spoofing():
    """VT-14 (vector adicional): un approver no puede usar el email de OTRO
    aprobador para que el empleado reciba un mail diciendo "aprobado por X"."""
    ts = _detailed_timesheet(100, owner_employee_id=2)
    gateway, _, _ = _setup_validate(
        timesheets={100: ts},
        requester_employee=Employee(id=1, email="approver@example.com", full_name="Approver"),
        team_member_ids=[2],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/timesheet/validate",
                json={
                    "approver_mail": "ceo@example.com",  # spoofing
                    "timesheetline_ids": [100],
                },
            )
            assert response.status_code == 403
            assert "nombre de otro" in response.json()["detail"].lower()
            gateway.validate.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_mixed_batch_all_or_nothing():
    """Lote con 1 propio + 1 ajeno → ninguno se valida (atomic)."""
    own = _detailed_timesheet(100, owner_employee_id=2)
    foreign = _detailed_timesheet(101, owner_employee_id=99)
    gateway, _, _ = _setup_validate(
        timesheets={100: own, 101: foreign},
        requester_employee=Employee(id=1, email="approver@example.com", full_name="Approver"),
        team_member_ids=[2],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/timesheet/validate",
                json={
                    "approver_mail": "approver@example.com",
                    "timesheetline_ids": [100, 101],
                },
            )
            assert response.status_code == 403
            gateway.validate.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_validate_returns_404_when_any_id_missing():
    """Algún ID inexistente → 404 antes del scope check."""
    gateway, _, _ = _setup_validate(
        timesheets={},
        requester_employee=Employee(id=1, email="approver@example.com", full_name="Approver"),
        team_member_ids=[2],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/timesheet/validate",
                json={
                    "approver_mail": "approver@example.com",
                    "timesheetline_ids": [999],
                },
            )
            assert response.status_code == 404
            gateway.validate.assert_not_called()
    finally:
        app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# Tests para POST /timesheet/review (mismo patrón, bonus de VT-14)
# ----------------------------------------------------------------------


@pytest.mark.integration
def test_review_blocks_idor_against_other_team():
    """`/timesheet/review` reusa el mismo helper. Scope ajeno → 403."""
    ts = _detailed_timesheet(100, owner_employee_id=99)
    gateway, _, _ = _setup_validate(
        timesheets={100: ts},
        requester_employee=Employee(id=1, email="approver@example.com", full_name="Approver"),
        team_member_ids=[2, 3],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/timesheet/review",
                json={
                    "approver_mail": "approver@example.com",
                    "timesheetline_ids": [100],
                    "body": "Revisar por favor",
                    "email_type": "review",
                },
            )
            assert response.status_code == 403
            gateway.validate.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_review_blocks_approver_mail_spoofing():
    """Mismo anti-spoofing en `/review`."""
    ts = _detailed_timesheet(100, owner_employee_id=2)
    gateway, _, _ = _setup_validate(
        timesheets={100: ts},
        requester_employee=Employee(id=1, email="approver@example.com", full_name="Approver"),
        team_member_ids=[2],
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/timesheet/review",
                json={
                    "approver_mail": "ceo@example.com",
                    "timesheetline_ids": [100],
                    "body": "Revisar",
                    "email_type": "review",
                },
            )
            assert response.status_code == 403
            assert "nombre de otro" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
