from datetime import date
from unittest.mock import Mock

from app.dashboard.infra.dashboard_service import OdooDashboardDataService
from app.project.domain.models import Project
from app.timesheet_line.domain.models import DetailedTimesheetLine


def _line(line_id, employee_id, hours):
    return DetailedTimesheetLine(
        id=line_id,
        name="x",
        employee_id=employee_id,
        project=Project(id=1, name="P"),
        task=None,
        hours=hours,
        date=date(2024, 1, 10),
        validated=False,
    )


class TestCalculateEmployeeTotals:
    """La lista de empleados del resumen incluye a quien aparece solo por proyecto."""

    def _service(self, names):
        employee_gateway = Mock()
        employee_gateway.get_by_ids.return_value = [
            Mock(id=i, full_name=n) for i, n in names.items()
        ]
        return OdooDashboardDataService(Mock(), employee_gateway, Mock(), Mock())

    def test_incluye_empleados_que_no_son_del_equipo(self):
        service = self._service({1: "Diana", 2: "Luca", 3: "Ana"})
        lines = [_line(1, 1, 36.0), _line(2, 2, 12.0)]

        result = service.calculate_employee_totals(lines, [{"id": 1}, {"id": 3}])

        by_id = {e.user_id: e.hours for e in result}
        assert by_id == {1: 36.0, 2: 12.0, 3: 0.0}
        assert sum(by_id.values()) == sum(line.hours for line in lines)

    def test_sin_equipo_solo_los_de_las_lineas(self):
        service = self._service({2: "Luca"})

        result = service.calculate_employee_totals([_line(1, 2, 8.0)], [])

        assert [(e.user_id, e.hours) for e in result] == [(2, 8.0)]
