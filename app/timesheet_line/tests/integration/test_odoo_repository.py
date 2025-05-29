from app.timesheet_line.domain.models import TimesheetLine, DetailedTimesheetLine
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from datetime import date
import pytest


@pytest.mark.integration  # type: ignore[attr-defined]
class TestOdooTimesheetLineGateway:
    @pytest.fixture(autouse=True)  # type: ignore[attr-defined]
    def setup(self):
        self.odoo_client = get_odoo_connection()
        self.gateway = OdooTimesheetLineGateway(self.odoo_client)
        yield
        # Limpieza después de cada test
        self._cleanup_test_data()

    def _cleanup_test_data(self):
        """Limpia los datos de prueba creados durante los tests"""
        test_lines = self.gateway.all()
        for line in test_lines:
            if "Test Timesheet Line" in line.name:
                if line.id:
                    self.gateway.delete(line.id)

    def test_returns_all_timesheet_lines_is_more_than_one(self):
        # Act
        lines = self.gateway.all()

        # Assert
        assert len(lines) > 0
        assert all(isinstance(line, DetailedTimesheetLine) for line in lines)
        assert all(hasattr(line, "employee_id") for line in lines)
        assert all(hasattr(line, "project") for line in lines)
        assert all(hasattr(line, "hours") for line in lines)
        assert all(hasattr(line, "date") for line in lines)
        # project es un objeto, aseguramos que tenga id y name
        assert all(hasattr(line.project, "id") for line in lines)
        assert all(hasattr(line.project, "name") for line in lines)

    def test_create_timesheet_line(self):
        # Arrange
        prev_lines = self.gateway.all()
        test_date = date(2021, 1, 1)
        test_name = "Test Timesheet Line"

        timesheet_line = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date,
            name=test_name,
        )

        # Act
        created_id = self.gateway.create(timesheet_line)
        post_lines = self.gateway.all()

        # Assert
        assert len(post_lines) == len(prev_lines) + 1
        created_line = next(
            (line for line in post_lines if line.id == created_id), None
        )
        assert created_line is not None
        assert created_line.id is not None
        assert isinstance(created_line.id, int)
        assert created_line.employee_id == 1
        assert created_line.project.id == 1
        assert created_line.hours == 1
        assert created_line.date == test_date
        assert created_line.name == test_name

    def test_delete_timesheet_line(self):
        # Arrange
        timesheet_line = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=date(2021, 1, 1),
            name="Test Timesheet Line",
        )
        created_id = self.gateway.create(timesheet_line)
        prev_lines = self.gateway.all()

        # Act
        assert created_id is not None
        delete_result = self.gateway.delete(created_id)
        post_lines = self.gateway.all()

        # Assert
        assert delete_result is True
        assert len(post_lines) == len(prev_lines) - 1
        assert not any(line.id == created_id for line in post_lines)

    def test_update_timesheet_line(self):
        # Arrange
        timesheet_line = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=date(2021, 1, 1),
            name="Test Timesheet Line",
        )
        created_id = self.gateway.create(timesheet_line)

        # Act - Actualizar
        updated_timesheet = TimesheetLine(
            id=created_id,
            employee_id=1,
            project_id=1,
            hours=2,  # Cambiamos las horas
            date=date(2021, 1, 1),
            name="Test Timesheet Line Updated",  # Cambiamos el nombre
        )
        update_result = self.gateway.update(updated_timesheet)

        # Assert
        assert update_result is True

        # Verificar que los cambios se aplicaron
        assert created_id is not None
        updated_line = self.gateway.get_by_id(created_id)
        assert updated_line is not None  # Nueva validación
        assert updated_line.id == created_id
        assert updated_line.hours == 2
        assert updated_line.name == "Test Timesheet Line Updated"
        assert updated_line.employee_id == 1
        assert updated_line.project.id == 1
        assert updated_line.date == date(2021, 1, 1)

    def test_filter_by_employee_id(self):
        """Test que verifica el filtrado por employee_id."""
        # Arrange
        timesheet_line = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=date(2021, 1, 1),
            name="Test Timesheet Line",
        )
        created_id = self.gateway.create(timesheet_line)

        # Act
        lines_employee_1 = self.gateway.all(employee_id=1)
        lines_employee_999 = self.gateway.all(employee_id=999)  # Employee que no existe

        # Assert
        assert any(line.id == created_id for line in lines_employee_1)
        assert not any(line.id == created_id for line in lines_employee_999)
        assert all(line.employee_id == 1 for line in lines_employee_1)

    def test_filter_by_date_range(self):
        """Test que verifica el filtrado por rango de fechas."""
        # Arrange
        test_date_1 = date(2024, 1, 15)
        test_date_2 = date(2024, 1, 20)
        test_date_3 = date(2024, 1, 25)

        timesheet_1 = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date_1,
            name="Test Timesheet Line 1",
        )
        timesheet_2 = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date_2,
            name="Test Timesheet Line 2",
        )
        timesheet_3 = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date_3,
            name="Test Timesheet Line 3",
        )

        created_id_1 = self.gateway.create(timesheet_1)
        created_id_2 = self.gateway.create(timesheet_2)
        created_id_3 = self.gateway.create(timesheet_3)

        # Act - Filtrar por rango que incluye solo las dos primeras
        lines_in_range = self.gateway.all(
            date_from=date(2024, 1, 14), date_to=date(2024, 1, 22)
        )

        # Assert
        created_ids_in_range = [
            line.id
            for line in lines_in_range
            if line.id in [created_id_1, created_id_2, created_id_3]
        ]
        assert created_id_1 in created_ids_in_range
        assert created_id_2 in created_ids_in_range
        assert created_id_3 not in created_ids_in_range

        # Verificar que todas las fechas están en el rango
        for line in lines_in_range:
            assert date(2024, 1, 14) <= line.date <= date(2024, 1, 22)

    def test_filter_by_date_from_only(self):
        """Test que verifica el filtrado solo con fecha de inicio."""
        # Arrange
        test_date_old = date(2024, 1, 10)
        test_date_new = date(2024, 1, 20)

        timesheet_old = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date_old,
            name="Test Timesheet Line Old",
        )
        timesheet_new = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date_new,
            name="Test Timesheet Line New",
        )

        created_id_old = self.gateway.create(timesheet_old)
        created_id_new = self.gateway.create(timesheet_new)

        # Act
        lines_from_date = self.gateway.all(date_from=date(2024, 1, 15))

        # Assert
        created_ids_from_date = [
            line.id
            for line in lines_from_date
            if line.id in [created_id_old, created_id_new]
        ]
        assert created_id_old not in created_ids_from_date
        assert created_id_new in created_ids_from_date

    def test_filter_by_date_to_only(self):
        """Test que verifica el filtrado solo con fecha de fin."""
        # Arrange
        test_date_old = date(2024, 1, 10)
        test_date_new = date(2024, 1, 20)

        timesheet_old = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date_old,
            name="Test Timesheet Line Old",
        )
        timesheet_new = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date_new,
            name="Test Timesheet Line New",
        )

        created_id_old = self.gateway.create(timesheet_old)
        created_id_new = self.gateway.create(timesheet_new)

        # Act
        lines_to_date = self.gateway.all(date_to=date(2024, 1, 15))

        # Assert
        created_ids_to_date = [
            line.id
            for line in lines_to_date
            if line.id in [created_id_old, created_id_new]
        ]
        assert created_id_old in created_ids_to_date
        assert created_id_new not in created_ids_to_date

    def test_filter_combined_employee_and_date_range(self):
        """Test que verifica el filtrado combinado por empleado y rango de fechas."""
        # Arrange
        test_date = date(2024, 1, 15)

        timesheet_emp1 = TimesheetLine(
            id=None,
            employee_id=1,
            project_id=1,
            hours=1,
            date=test_date,
            name="Test Timesheet Line Emp1",
        )
        timesheet_emp2 = TimesheetLine(
            id=None,
            employee_id=2,
            project_id=1,
            hours=1,
            date=test_date,
            name="Test Timesheet Line Emp2",
        )

        created_id_emp1 = self.gateway.create(timesheet_emp1)
        created_id_emp2 = self.gateway.create(timesheet_emp2)

        # Act
        lines_filtered = self.gateway.all(
            employee_id=1, date_from=date(2024, 1, 14), date_to=date(2024, 1, 16)
        )

        # Assert
        created_ids_filtered = [
            line.id
            for line in lines_filtered
            if line.id in [created_id_emp1, created_id_emp2]
        ]
        assert created_id_emp1 in created_ids_filtered
        assert created_id_emp2 not in created_ids_filtered

        # Verificar que todos los resultados son del empleado correcto y en el rango de fechas
        for line in lines_filtered:
            assert line.employee_id == 1
            assert date(2024, 1, 14) <= line.date <= date(2024, 1, 16)

    def test_get_by_id_not_found(self):
        """Test que verifica que get_by_id devuelve None cuando no encuentra el timesheet."""
        # Act
        result = self.gateway.get_by_id(99999)  # ID que no existe

        # Assert
        assert result is None

    def test_delete_timesheet_not_found(self):
        """Test que verifica el comportamiento de delete cuando el timesheet no existe."""
        # Act & Assert
        # En Odoo, delete lanza una excepción cuando el registro no existe
        with pytest.raises(Exception) as exc_info:
            self.gateway.delete(99999)  # ID que no existe

        # Verificar que es el tipo de error esperado de Odoo
        assert "Record does not exist" in str(exc_info.value)
