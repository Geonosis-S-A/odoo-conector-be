from app.timesheet_line.domain.models import TimesheetLine, DetailedTimesheetLine
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from datetime import date, datetime, timedelta
from app.timesheet_line.tests.utils.date_utils import (
    get_valid_test_date,
    get_multiple_test_dates
)
import pytest


def get_valid_test_date_obj(days_from_today: int = 7) -> date:
    """Convierte una fecha de test válida a objeto date."""
    date_str = get_valid_test_date(days_from_today)
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def get_multiple_test_date_objs(count: int = 3, start_days_from_today: int = 7) -> list[date]:
    """Convierte múltiples fechas de test válidas a objetos date."""
    date_strs = get_multiple_test_dates(count, start_days_from_today)
    return [datetime.strptime(date_str, "%Y-%m-%d").date() for date_str in date_strs]


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
                date=get_valid_test_date_obj(),
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
        # La fecha debe coincidir con la fecha de test generada dinámicamente
        expected_date = get_valid_test_date_obj()
        assert created_line.date == expected_date
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
                date=get_valid_test_date_obj(),
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
                date=get_valid_test_date_obj(),
                name="Test Timesheet Line 1",
            ),
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=2,
                date=get_valid_test_date_obj(8),
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
                date=get_valid_test_date_obj(),
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
            date=get_valid_test_date_obj(),
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
        expected_date = get_valid_test_date_obj()
        assert updated_line.date == expected_date

    def test_filter_by_employee_id(self):
        """Test que verifica el filtrado por employee_id."""
        # Arrange
        timesheet_lines = [
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=1,
                date=get_valid_test_date_obj(),
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
        test_dates = get_multiple_test_date_objs(3)
        test_date_1 = test_dates[0]
        test_date_2 = test_dates[1]
        test_date_3 = test_dates[2]

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
        # Filtrar entre la primera y segunda fecha de test
        lines_in_range = self.gateway.all(
            date_from=test_date_1,
            date_to=test_date_2,
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
            assert test_date_1 <= line.date <= test_date_2

    def test_filter_by_date_from_only(self):
        """Test que verifica el filtrado solo con fecha de inicio."""
        # Arrange
        test_dates = get_multiple_test_date_objs(2)
        test_date_old = test_dates[0]
        test_date_new = test_dates[1]

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
            date_from=test_date_new
        )

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
        test_dates = get_multiple_test_date_objs(2)
        test_date_old = test_dates[0]
        test_date_new = test_dates[1]

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
            date_to=test_date_old
        )

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
        test_date = get_valid_test_date_obj()

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
                date=get_valid_test_date_obj(10),  # Fecha diferente para el test
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
            date_from=test_date,
            date_to=test_date,
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
            assert line.date == test_date

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
                date=get_valid_test_date_obj(),
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
                date=get_valid_test_date_obj(),
                name="Test Timesheet Line 1 for Validation",
            ),
            TimesheetLine(
                id=None,
                employee_id=1,
                project_id=1,
                hours=2,
                date=get_valid_test_date_obj(8),
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
