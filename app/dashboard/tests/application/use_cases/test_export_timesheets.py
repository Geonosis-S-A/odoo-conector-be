from datetime import date
from unittest.mock import Mock

import pytest

from app.dashboard.application.use_cases.export_timesheets import (
    ExportTimesheetsByTeamUseCase,
)

LINE = {
    "id": 1,
    "name": "x",
    "date": "2024-01-10",
    "unit_amount": 2.0,
    "employee_id": [7, "Luca"],
    "project_id": [152, "Proyecto"],
    "task_id": False,
    "create_date": "2024-01-10 10:00:00",
    "validated": False,
}


class TestExportTimesheetsByTeamUseCase:
    """El Excel usa la misma regla de equipo que el resumen del dashboard."""

    @pytest.fixture
    def gateways(self):
        timesheet = Mock()
        timesheet.get_team_users.return_value = [{"id": 1}, {"id": 2}]
        timesheet.all_by_employees_with_requester_user_id.return_value = [LINE]
        employee = Mock()
        employee.get_user_id_by_employee_id.return_value = 42
        task = Mock()
        assignment = Mock()
        return timesheet, employee, task, assignment

    def _use_case(self, gateways):
        timesheet, employee, task, assignment = gateways
        return ExportTimesheetsByTeamUseCase(timesheet, employee, task, 10, assignment)

    def test_pm_puro_no_suma_jerarquia(self, gateways):
        timesheet, _, _, assignment = gateways
        assignment.is_project_manager_only.return_value = True

        self._use_case(gateways).execute(date(2024, 1, 1), date(2024, 1, 31))

        assignment.is_project_manager_only.assert_called_once_with(42)
        timesheet.get_team_users.assert_not_called()
        timesheet.all_by_employees_with_requester_user_id.assert_called_once_with(
            [], date(2024, 1, 1), date(2024, 1, 31), 42
        )

    def test_delivery_suma_jerarquia(self, gateways):
        timesheet, _, _, assignment = gateways
        assignment.is_project_manager_only.return_value = False

        self._use_case(gateways).execute(date(2024, 1, 1), date(2024, 1, 31))

        timesheet.get_team_users.assert_called_once_with(42, 10)
        timesheet.all_by_employees_with_requester_user_id.assert_called_once_with(
            [1, 2], date(2024, 1, 1), date(2024, 1, 31), 42
        )


from app.task.domain.models import TaskWithParentInfo


def _task(id_, name, parent=None, parent_name=None):
    return TaskWithParentInfo(
        id=id_,
        name=name,
        project_id=152,
        project_name="Proyecto",
        parent_id=parent,
        parent_name=parent_name,
    )


class TestExportGestionInterna:
    """Las licencias cargadas como horas deben verse en el Excel con su tipo."""

    def _run(self, lines, tasks):
        timesheet = Mock()
        timesheet.get_team_users.return_value = [{"id": 7}]
        timesheet.all_by_employees_with_requester_user_id.return_value = lines
        employee = Mock()
        employee.get_user_id_by_employee_id.return_value = 42
        task_gw = Mock()
        task_gw.get_tasks_info_with_parents.side_effect = lambda ids: {
            i: tasks[i] for i in ids if i in tasks
        }
        assignment = Mock()
        assignment.is_project_manager_only.return_value = False
        uc = ExportTimesheetsByTeamUseCase(timesheet, employee, task_gw, 10, assignment)
        return uc.execute(date(2024, 1, 1), date(2024, 1, 31))

    def _line(self, id_, task_id, validated=False):
        return {**LINE, "id": id_, "task_id": task_id, "validated": validated}

    def test_subtarea_de_gestion_interna_informa_el_tipo(self):
        tasks = {
            10: _task(10, "Gestión interna"),
            11: _task(11, "Licencia por enfermedad", 10, "Gestión interna"),
        }
        df = self._run([self._line(1, [11, "Licencia por enfermedad"])], tasks)
        assert df.iloc[0]["tipo_licencia"] == "Licencia por enfermedad"
        assert df.iloc[0]["tarea"] == "Gestión interna"
        assert df.iloc[0]["subtarea_1"] == "Licencia por enfermedad"

    def test_carga_directa_en_gestion_interna(self):
        tasks = {10: _task(10, "Gestión interna")}
        df = self._run([self._line(1, [10, "Gestión interna"])], tasks)
        assert df.iloc[0]["tipo_licencia"] == "Gestión interna"

    def test_nombre_en_otra_capitalizacion(self):
        tasks = {
            10: _task(10, "GESTION INTERNA "),
            11: _task(11, "Días de estudio", 10, "GESTION INTERNA "),
        }
        df = self._run([self._line(1, [11, "Días de estudio"])], tasks)
        assert df.iloc[0]["tipo_licencia"] == "Días de estudio"

    def test_tarea_comun_y_sin_tarea_tienen_tipo_vacio(self):
        tasks = {20: _task(20, "Desarrollo")}
        df = self._run(
            [self._line(1, [20, "Desarrollo"]), self._line(2, False)], tasks
        )
        assert list(df["tipo_licencia"]) == ["", ""]

    def test_columna_validada_indica_aprobacion(self):
        tasks = {10: _task(10, "Gestión interna")}
        df = self._run(
            [
                self._line(1, [10, "Gestión interna"], validated=True),
                self._line(2, [10, "Gestión interna"], validated=False),
            ],
            tasks,
        )
        assert sorted(df["validada"]) == ["No", "Sí"]

    def test_nombre_sin_tilde(self):
        tasks = {
            10: _task(10, "Gestion interna"),
            11: _task(11, "Sin Asignación", 10, "Gestion interna"),
        }
        df = self._run([self._line(1, [11, "Sin Asignación"])], tasks)
        assert df.iloc[0]["tipo_licencia"] == "Sin Asignación"
