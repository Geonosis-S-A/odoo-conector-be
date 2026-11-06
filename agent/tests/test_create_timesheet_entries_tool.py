"""Herramienta `create_timesheet_entries` del asistente de IA.

Tras GEO-954, CargarHorasUseCase exige el gateway de asignaciones. La herramienta
lo armaba con un solo argumento y fallaba siempre con "Error inesperado" (TypeError).
Estos tests usan datos simulados: no tocan Odoo.
"""

import json
from datetime import date
from types import SimpleNamespace

import pytest

from agent.tools import project_tools


class _FakeTimesheetGateway:
    def __init__(self):
        self.created = []

    def create(self, lines):
        self.created.extend(lines)
        return [101]

    def get_by_ids(self, ids):
        return [
            SimpleNamespace(
                id=101,
                employee_id=7,
                project=SimpleNamespace(id=55, name="Proyecto X"),
                hours=8.0,
                date=date(2026, 11, 2),
                name="",
                validated=False,
                task=None,
            )
        ]


class _FakeAssignments:
    def __init__(self, assigned: bool):
        self.assigned = assigned

    def is_employee_assigned(self, employee_id, project_id, on_date):
        return self.assigned

    def get_project_manager_user_ids(self, project_ids):
        return {}

    def get_project_name(self, project_id):
        return "Proyecto X"

    def get_assignment_start_date(self, employee_id, project_id):
        return None


class _FakeEmployees:
    def get_user_id_by_employee_id(self, employee_id):
        return None


_ENTRIES = json.dumps(
    [{"project_id": 55, "task_id": None, "hours": 8.0, "date_str": "2026-11-02"}]
)


def _run(monkeypatch, assigned: bool):
    timesheets = _FakeTimesheetGateway()
    monkeypatch.setattr(project_tools, "get_odoo_connection", lambda: object())
    monkeypatch.setattr(project_tools, "OdooTimesheetLineGateway", lambda c: timesheets)
    monkeypatch.setattr(
        project_tools, "OdooProjectAssignmentGateway", lambda c: _FakeAssignments(assigned)
    )
    monkeypatch.setattr(project_tools, "OdooEmployeeGateway", lambda c: _FakeEmployees())
    runtime = SimpleNamespace(context=SimpleNamespace(employee_id=7))
    result = json.loads(project_tools.create_timesheet_entries.func(runtime, _ENTRIES))
    return result, timesheets


def test_carga_horas_en_proyecto_asignado(monkeypatch):
    result, timesheets = _run(monkeypatch, assigned=True)

    assert result["success"] is True, result
    assert result["total_created"] == 1
    assert len(timesheets.created) == 1


def test_proyecto_sin_asignacion_explica_el_motivo_y_no_crea_nada(monkeypatch):
    result, timesheets = _run(monkeypatch, assigned=False)

    assert result["success"] is False
    assert result["error"] == "Sin asignación al proyecto"
    assert "Proyecto X" in result["message"]
    assert timesheets.created == []
