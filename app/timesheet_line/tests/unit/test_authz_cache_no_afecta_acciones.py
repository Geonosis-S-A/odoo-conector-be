"""Con la caché de autoridad tibia, validar y borrar deben seguir decidiendo con
lo que dice Odoo en ese momento. Se usa el TeamAccessService real (no un mock)."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from app.project.domain.models import Project
from app.team.application import team_access as ta
from app.team.application.team_access import TeamAccessService
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetDeleteForbiddenError,
    TimesheetValidateError,
)
from app.timesheet_line.application.use_cases.delete_timesheet import (
    DeleteTimesheetUseCase,
)
from app.timesheet_line.application.use_cases.validar_timesheet import (
    ValidateTimesheetUseCase,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine

ACTOR = 5  # empleado que valida/borra (user Odoo 100)
OWNER = 7  # dueño de la línea
PROJECT = 1


@pytest.fixture(autouse=True)
def _cache_activa(monkeypatch):
    for cache in (ta._USER_ID_CACHE, ta._LED_PROJECTS_CACHE, ta._APPROVERS_CACHE):
        monkeypatch.setattr(cache, "ttl_seconds", 60)


@pytest.fixture
def odoo():
    """Estado de Odoo que los tests pueden cambiar a mitad del escenario."""
    state = {"approvers": [(100, "Gerente")]}
    employee_gateway = Mock()
    employee_gateway.get_user_id_by_employee_id.return_value = 100
    employee_gateway.get_by_email.return_value = Mock(id=ACTOR)
    employee_gateway.get_by_ids.return_value = []

    assignment_gateway = Mock()
    assignment_gateway.get_project_approvers.side_effect = lambda ids: {
        i: list(state["approvers"]) for i in ids
    }
    assignment_gateway.get_led_projects.side_effect = lambda uid: (
        [Project(id=PROJECT, name="P", manager_user_id=uid)]
        if (100, "Gerente") in state["approvers"]
        else []
    )
    timesheet_gateway = Mock()
    timesheet_gateway.get_by_ids.return_value = [
        DetailedTimesheetLine(
            id=10,
            name="ts",
            employee_id=OWNER,
            project=Project(id=PROJECT, name="P"),
            task=None,
            hours=8.0,
            date=date(2026, 10, 8),
            validated=False,
        )
    ]
    service = TeamAccessService(
        employee_gateway,
        assignment_gateway,
        timesheet_gateway,
        Mock(list_by_member=lambda _: []),
    )
    return Mock(
        state=state,
        service=service,
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
    )


def _calentar_cache_y_quitar_gerencia(odoo):
    # Una vista de lectura llena la caché...
    assert odoo.service.manages_project(ACTOR, PROJECT, cached=True) is True
    assert odoo.service.lines_authority(
        ACTOR, [(OWNER, PROJECT)], cached=True
    ) == {(OWNER, PROJECT): True}
    # ...y después le sacan la gerencia en Odoo.
    odoo.state["approvers"] = [(999, "Otro gerente")]


def test_la_lectura_puede_mostrar_el_dato_viejo_hasta_el_ttl(odoo):
    """Comportamiento aceptado y documentado: solo las vistas de lectura."""
    _calentar_cache_y_quitar_gerencia(odoo)

    assert odoo.service.lines_authority(
        ACTOR, [(OWNER, PROJECT)], cached=True
    ) == {(OWNER, PROJECT): True}


async def test_validar_se_niega_aunque_la_cache_este_tibia(odoo):
    _calentar_cache_y_quitar_gerencia(odoo)
    use_case = ValidateTimesheetUseCase(
        odoo.timesheet_gateway,
        AsyncMock(),
        odoo.employee_gateway,
        Mock(),
        odoo.service,
    )

    with pytest.raises(TimesheetValidateError, match="no gerenciás su proyecto"):
        await use_case.execute([10], "a@x.com", validator_employee_id=ACTOR)

    odoo.timesheet_gateway.validate.assert_not_called()


def test_borrar_se_niega_aunque_la_cache_este_tibia(odoo):
    _calentar_cache_y_quitar_gerencia(odoo)
    use_case = DeleteTimesheetUseCase(odoo.timesheet_gateway, odoo.service)

    with pytest.raises(TimesheetDeleteForbiddenError):
        use_case.execute([10], requester_employee_id=ACTOR)

    odoo.timesheet_gateway.delete.assert_not_called()
