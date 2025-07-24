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
                    self.gateway.delete([line.id])

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
        """Test que verifica la creación de una línea de timesheet."""
        # Arrange
        timesheet_lines = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=date(2025, 8, 1),  # Cambio: fecha futura
                name="Test Timesheet Line",
            )
        ]

        # Act
        created_ids = self.gateway.create(timesheet_lines)

        # Assert
        assert created_ids is not None
        assert len(created_ids) == 1
        created_id = created_ids[0]
        assert isinstance(created_id, int)
        assert created_id > 0

        # Verificar que se puede obtener la línea creada
        created_line = self.gateway.get_by_id(created_id)
        assert created_line is not None
        assert created_line.id == created_id
        assert created_line.employee_id == 1
        assert created_line.project.id == 1
        assert created_line.hours == 1
        assert created_line.date == date(2025, 8, 1)
        assert created_line.name == "Test Timesheet Line"

    def test_delete_timesheet_line(self):
        """Test que verifica la eliminación de una línea de timesheet."""
        # Arrange
        timesheet_lines = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=date(2025, 8, 1),  # Cambio: fecha futura
                name="Test Timesheet Line",
            )
        ]
        created_ids = self.gateway.create(timesheet_lines)
        assert created_ids is not None
        created_id = created_ids[0]

        # Act
        delete_result = self.gateway.delete([created_id])

        # Assert
        assert delete_result is True

        # Verificar que la línea ya no existe
        deleted_line = self.gateway.get_by_id(created_id)
        assert deleted_line is None

    def test_delete_multiple_timesheet_lines(self):
        """Test que verifica la eliminación de múltiples líneas de timesheet."""
        # Arrange
        timesheet_lines = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=date(2025, 8, 1),  # Cambio: fecha futura
                name="Test Timesheet Line 1",
            ),
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=2,
                date=date(2025, 8, 2),  # Cambio: fecha futura
                name="Test Timesheet Line 2",
            ),
        ]
        created_ids = self.gateway.create(timesheet_lines)
        assert created_ids is not None
        assert len(created_ids) == 2

        # Act
        delete_result = self.gateway.delete(created_ids)

        # Assert
        assert delete_result is True

        # Verificar que las líneas ya no existen
        for created_id in created_ids:
            deleted_line = self.gateway.get_by_id(created_id)
            assert deleted_line is None

    def test_update_timesheet_line(self):
        """Test que verifica la actualización de una línea de timesheet."""
        # Arrange
        timesheet_lines = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=date(2025, 8, 1),  # Cambio: fecha futura
                name="Test Timesheet Line",
            )
        ]
        created_ids = self.gateway.create(timesheet_lines)
        assert created_ids is not None
        created_id = created_ids[0]

        # Act - Actualizar
        updated_timesheet = TimesheetLine(
            id=created_id,
            employee_id=1,
            project_id=1,
            hours=2,  # Cambiamos las horas
            date=date(2025, 8, 1),  # Cambio: fecha futura
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
        assert updated_line.date == date(2025, 8, 1)

    def test_filter_by_employee_id(self):
        """Test que verifica el filtrado por employee_id."""
        # Arrange
        timesheet_lines = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=date(2025, 8, 1),  # Cambio: fecha futura
                name="Test Timesheet Line",
            )
        ]
        created_ids = self.gateway.create(timesheet_lines)
        assert created_ids is not None
        created_id = created_ids[0]

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
        test_date_1 = date(2025, 8, 15)  # Cambio: fecha futura
        test_date_2 = date(2025, 8, 20)  # Cambio: fecha futura
        test_date_3 = date(2025, 8, 25)  # Cambio: fecha futura

        timesheet_lines_1 = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=test_date_1,
                name="Test Timesheet Line 1",
            )
        ]
        timesheet_lines_2 = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=test_date_2,
                name="Test Timesheet Line 2",
            )
        ]
        timesheet_lines_3 = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=test_date_3,
                name="Test Timesheet Line 3",
            )
        ]

        created_ids_1 = self.gateway.create(timesheet_lines_1)
        created_ids_2 = self.gateway.create(timesheet_lines_2)
        created_ids_3 = self.gateway.create(timesheet_lines_3)

        assert (
            created_ids_1 is not None
            and created_ids_2 is not None
            and created_ids_3 is not None
        )
        created_id_1 = created_ids_1[0]
        created_id_2 = created_ids_2[0]
        created_id_3 = created_ids_3[0]

        # Act - Filtrar por rango que incluye solo las dos primeras
        lines_in_range = self.gateway.all(
            date_from=date(2025, 8, 14),
            date_to=date(2025, 8, 22),  # Cambio: fechas futuras
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
            assert date(2025, 8, 14) <= line.date <= date(2025, 8, 22)

    def test_filter_by_date_from_only(self):
        """Test que verifica el filtrado solo con fecha de inicio."""
        # Arrange
        test_date_old = date(2025, 8, 10)  # Cambio: fecha futura
        test_date_new = date(2025, 8, 20)  # Cambio: fecha futura

        timesheet_lines_old = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=test_date_old,
                name="Test Timesheet Line Old",
            )
        ]
        timesheet_lines_new = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=test_date_new,
                name="Test Timesheet Line New",
            )
        ]

        created_ids_old = self.gateway.create(timesheet_lines_old)
        created_ids_new = self.gateway.create(timesheet_lines_new)

        assert created_ids_old is not None and created_ids_new is not None
        created_id_old = created_ids_old[0]
        created_id_new = created_ids_new[0]

        # Act
        lines_from_date = self.gateway.all(
            date_from=date(2025, 8, 15)
        )  # Cambio: fecha futura

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
        test_date_old = date(2025, 8, 10)  # Cambio: fecha futura
        test_date_new = date(2025, 8, 20)  # Cambio: fecha futura

        timesheet_lines_old = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=test_date_old,
                name="Test Timesheet Line Old",
            )
        ]
        timesheet_lines_new = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=test_date_new,
                name="Test Timesheet Line New",
            )
        ]

        created_ids_old = self.gateway.create(timesheet_lines_old)
        created_ids_new = self.gateway.create(timesheet_lines_new)

        assert created_ids_old is not None and created_ids_new is not None
        created_id_old = created_ids_old[0]
        created_id_new = created_ids_new[0]

        # Act
        lines_to_date = self.gateway.all(
            date_to=date(2025, 8, 15)
        )  # Cambio: fecha futura

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
        test_date = date(2025, 8, 15)  # Cambio: fecha futura

        timesheet_lines_emp1 = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=test_date,
                name="Test Timesheet Line Emp1",
            )
        ]
        # Crear un segundo timesheet para el mismo empleado en una fecha diferente
        timesheet_lines_emp1_diff_date = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=date(
                    2025, 8, 10
                ),  # Cambio: fecha futura, fuera del rango de filtro
                name="Test Timesheet Line Emp1 Old",
            )
        ]

        created_ids_emp1 = self.gateway.create(timesheet_lines_emp1)
        created_ids_emp1_old = self.gateway.create(timesheet_lines_emp1_diff_date)

        assert created_ids_emp1 is not None and created_ids_emp1_old is not None
        created_id_emp1 = created_ids_emp1[0]
        created_id_emp1_old = created_ids_emp1_old[0]

        # Act
        lines_filtered = self.gateway.all(
            employee_id=1,
            date_from=date(2025, 8, 14),
            date_to=date(2025, 8, 16),  # Cambio: fechas futuras
        )

        # Assert
        created_ids_filtered = [
            line.id
            for line in lines_filtered
            if line.id in [created_id_emp1, created_id_emp1_old]
        ]
        assert created_id_emp1 in created_ids_filtered
        assert (
            created_id_emp1_old not in created_ids_filtered
        )  # Fuera del rango de fechas

        # Verificar que todos los resultados son del empleado correcto y en el rango de fechas
        for line in lines_filtered:
            assert line.employee_id == 1
            assert date(2025, 8, 14) <= line.date <= date(2025, 8, 16)

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
            self.gateway.delete([99999])  # ID que no existe

        # Verificar que es el tipo de error esperado de Odoo
        assert "Record does not exist" in str(exc_info.value)

    def test_validate_timesheet_line(self):
        """Test que verifica la validación de una línea de timesheet."""
        # Arrange
        timesheet_lines = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=date(2025, 8, 1),  # Cambio: fecha futura
                name="Test Timesheet Line for Validation",
            )
        ]
        created_ids = self.gateway.create(timesheet_lines)
        assert created_ids is not None
        created_id = created_ids[0]

        # Act
        validate_result = self.gateway.validate([created_id])

        # Assert
        assert validate_result is True

        # Verificar que la línea aún existe (validate no debe eliminar)
        updated_line = self.gateway.get_by_id(created_id)
        assert updated_line is not None
        assert updated_line.id == created_id

    def test_validate_multiple_timesheet_lines(self):
        """Test que verifica la validación de múltiples líneas de timesheet."""
        # Arrange
        timesheet_lines = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=date(2025, 8, 1),  # Cambio: fecha futura
                name="Test Timesheet Line 1 for Validation",
            ),
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=2,
                date=date(2025, 8, 2),  # Cambio: fecha futura
                name="Test Timesheet Line 2 for Validation",
            ),
        ]
        created_ids = self.gateway.create(timesheet_lines)
        assert created_ids is not None
        assert len(created_ids) == 2

        # Act
        validate_result = self.gateway.validate(created_ids)

        # Assert
        assert validate_result is True

        # Verificar que las líneas aún existen
        for created_id in created_ids:
            updated_line = self.gateway.get_by_id(created_id)
            assert updated_line is not None
            assert updated_line.id == created_id

    def test_validate_empty_list(self):
        """Test que verifica la validación con lista vacía de IDs."""
        # Act
        validate_result = self.gateway.validate([])

        # Assert
        assert validate_result is True

    def test_validate_timesheet_not_found(self):
        """Test que verifica el comportamiento de validate cuando el timesheet no existe."""
        # Act & Assert
        # En Odoo, validate con un ID inexistente puede lanzar una excepción o devolver False
        # Dependiendo de la implementación exacta de Odoo
        with pytest.raises(Exception) as exc_info:
            self.gateway.validate([99999])  # ID que no existe

        # Verificar que es el tipo de error esperado de Odoo
        assert (
            "Record does not exist" in str(exc_info.value)
            or "not found" in str(exc_info.value).lower()
        )
