"""Rechazar horas (POST /timesheet/review): requiere el rol approver Y autoridad
sobre cada línea (gerente o PM de su proyecto)."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.email.api.dependencies import get_common_email_service
from app.main import app
from app.project.domain.models import Project
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles
from app.team.api.dependencies import get_team_access_service
from app.timesheet_line.api import routers as timesheet_routers
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetReviewForbiddenError,
)
from app.timesheet_line.application.use_cases.review_timesheets import (
    ReviewTimesheetsUseCase,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.users.domain.models import Employee

USER = 5
BODY = {
    "timesheetline_ids": [1, 2],
    "approver_mail": "lider@x.com",
    "email_type": "review",
}


def _line(line_id: int, employee_id: int, project_id: int) -> DetailedTimesheetLine:
    return DetailedTimesheetLine(
        id=line_id,
        name=f"ts-{line_id}",
        employee_id=employee_id,
        project=Project(id=project_id, name="P"),
        task=None,
        hours=8.0,
        date=date(2026, 10, 1),
        validated=False,
    )


@pytest.fixture
def parts():
    employee_gateway = Mock()
    employee_gateway.get_by_email.return_value = Employee(
        id=USER, email="lider@x.com", full_name="Líder"
    )
    employee_gateway.get_by_id.side_effect = lambda eid: Employee(
        id=eid, email=f"e{eid}@x.com", full_name=f"E{eid}"
    )
    timesheet_gateway = Mock()
    timesheet_gateway.get_by_ids.return_value = [_line(1, 7, 10), _line(2, 8, 20)]
    email_service = Mock()
    email_service.send_timesheet_mail = AsyncMock()
    return Mock(
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
        email_service=email_service,
        notifications=Mock(),
        team_access=Mock(),
    )


def _use_case(p) -> ReviewTimesheetsUseCase:
    return ReviewTimesheetsUseCase(
        p.employee_gateway,
        p.timesheet_gateway,
        p.email_service,
        p.notifications,
        p.team_access,
    )


class TestReviewUseCase:
    @pytest.mark.asyncio
    async def test_con_autoridad_en_todas_las_lineas_envia(self, parts):
        parts.team_access.lines_authority.return_value = {(7, 10): True, (8, 20): True}

        ok = await _use_case(parts).execute(
            [1, 2], "lider@x.com", reviewer_employee_id=USER
        )

        assert ok is True
        assert parts.email_service.send_timesheet_mail.await_count == 2

    @pytest.mark.asyncio
    async def test_una_linea_de_proyecto_ajeno_rechaza_todo_y_no_envia(self, parts):
        parts.team_access.lines_authority.return_value = {
            (7, 10): True,
            (8, 20): False,
        }

        with pytest.raises(TimesheetReviewForbiddenError) as exc:
            await _use_case(parts).execute(
                [1, 2], "lider@x.com", reviewer_employee_id=USER
            )

        assert "[2]" in exc.value.message
        parts.email_service.send_timesheet_mail.assert_not_awaited()
        parts.notifications.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_la_autoridad_se_consulta_sin_cache(self, parts):
        parts.team_access.lines_authority.return_value = {(7, 10): True, (8, 20): True}

        await _use_case(parts).execute([1, 2], "lider@x.com", reviewer_employee_id=USER)

        (args, kwargs) = parts.team_access.lines_authority.call_args
        assert args[0] == USER
        assert set(args[1]) == {(7, 10), (8, 20)}
        assert not kwargs.get("cached")

    @pytest.mark.asyncio
    async def test_las_propias_horas_no_se_rechazan(self, parts):
        # lines_authority nunca da autoridad sobre las propias horas del actor
        parts.timesheet_gateway.get_by_ids.return_value = [_line(1, USER, 10)]
        parts.team_access.lines_authority.return_value = {(USER, 10): False}

        with pytest.raises(TimesheetReviewForbiddenError):
            await _use_case(parts).execute(
                [1], "lider@x.com", reviewer_employee_id=USER
            )


class TestReviewEndpoint:
    @pytest.fixture
    def client(self, parts):
        def _make(roles):
            app.dependency_overrides[get_current_user] = lambda: {
                "user_id": USER,
                "roles": roles,
            }
            app.dependency_overrides[get_team_access_service] = lambda: parts.team_access
            app.dependency_overrides[get_common_email_service] = lambda: parts.email_service
            app.dependency_overrides[timesheet_routers.get_employee_gateway] = (
                lambda: parts.employee_gateway
            )
            app.dependency_overrides[timesheet_routers.get_timesheet_gateway] = (
                lambda: parts.timesheet_gateway
            )
            app.dependency_overrides[timesheet_routers.get_notification_repository] = (
                lambda: parts.notifications
            )
            return TestClient(app)

        try:
            yield _make
        finally:
            app.dependency_overrides.clear()

    def test_sin_el_rol_es_403_aunque_gerencie_el_proyecto(self, client, parts):
        parts.team_access.lines_authority.return_value = {(7, 10): True, (8, 20): True}

        response = client([]).post("/api/v1/timesheet/review", json=BODY)

        assert response.status_code == 403
        parts.team_access.lines_authority.assert_not_called()
        parts.email_service.send_timesheet_mail.assert_not_awaited()

    def test_con_el_rol_pero_proyecto_ajeno_es_403(self, client, parts):
        parts.team_access.lines_authority.return_value = {
            (7, 10): True,
            (8, 20): False,
        }

        response = client([int(Roles.approver)]).post(
            "/api/v1/timesheet/review", json=BODY
        )

        assert response.status_code == 403
        assert "no gerenciás su proyecto" in response.json()["detail"]
        parts.email_service.send_timesheet_mail.assert_not_awaited()

    def test_con_el_rol_y_autoridad_responde_ok(self, client, parts):
        parts.team_access.lines_authority.return_value = {(7, 10): True, (8, 20): True}

        response = client([int(Roles.approver)]).post(
            "/api/v1/timesheet/review", json=BODY
        )

        assert response.status_code == 200
        assert response.json() == {"success": True}
