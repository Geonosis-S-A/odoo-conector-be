from datetime import date
import pytest
from unittest.mock import Mock

from app.timesheet_line.application.use_cases.obtener_horas import (
    ListTimesheetLinesUseCase,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from app.users.domain.repositories import EmployeeGateway
from app.timesheet_line.application.excepctions.exceptions import (
    InvalidEmployeeIdError,
    EmployeeNotExistsError,
    InvalidDateRangeError,
    TimesheetListError,
)


class TestListTimesheetLinesUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=OdooTimesheetLineGateway)

    @pytest.fixture
    def mock_employee_gateway(self):
        return Mock(spec=EmployeeGateway)

    @pytest.fixture
    def use_case(self, mock_gateway, mock_employee_gateway):
        return ListTimesheetLinesUseCase(mock_gateway, mock_employee_gateway)

    @pytest.fixture
    def sample_timesheet_lines(self):
        return [
            DetailedTimesheetLine(
                id=1,
                name="Test Timesheet 1",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 1, 15),
            ),
            DetailedTimesheetLine(
                id=2,
                name="Test Timesheet 2",
                employee_id=2,
                project=Project(id=2, name="Test Project 2"),
                task=None,
                hours=4.0,
                date=date(2024, 1, 20),
            ),
        ]

    def test_execute_success_with_required_params(
        self, use_case, mock_gateway, mock_employee_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución exitosa con parámetros obligatorios."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)

        mock_employee_gateway.exists_by_id.return_value = True
        mock_gateway.all.return_value = sample_timesheet_lines

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_gateway.all.assert_called_once_with(employee_id, date_from, date_to)
        assert result == sample_timesheet_lines

    def test_execute_returns_empty_list_when_no_results(
        self, use_case, mock_gateway, mock_employee_gateway
    ):
        """Test que verifica que se devuelve una lista vacía cuando no hay resultados."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)

        mock_employee_gateway.exists_by_id.return_value = True
        mock_gateway.all.return_value = []  # Sin resultados

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        assert result == []
        assert isinstance(result, list)
        assert len(result) == 0
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_gateway.all.assert_called_once_with(employee_id, date_from, date_to)

    def test_execute_with_specific_employee_and_date_range(
        self, use_case, mock_gateway, mock_employee_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución con empleado específico y rango de fechas."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 16)

        mock_employee_gateway.exists_by_id.return_value = True
        mock_gateway.all.return_value = [
            sample_timesheet_lines[0]
        ]  # Solo el primer timesheet

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_gateway.all.assert_called_once_with(employee_id, date_from, date_to)
        assert len(result) == 1
        assert result[0].employee_id == employee_id
        assert date_from <= result[0].date <= date_to

    # TESTS PARA VALIDACIONES
    def test_execute_invalid_employee_id_negative(self, use_case):
        """Test que verifica error con employee_id negativo."""
        # Arrange
        employee_id = -1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)

        # Act & Assert
        with pytest.raises(InvalidEmployeeIdError) as exc_info:
            use_case.execute(employee_id, date_from, date_to)

        assert "-1" in str(exc_info.value.message)

    def test_execute_invalid_employee_id_zero(self, use_case):
        """Test que verifica error con employee_id cero."""
        # Arrange
        employee_id = 0
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)

        # Act & Assert
        with pytest.raises(InvalidEmployeeIdError) as exc_info:
            use_case.execute(employee_id, date_from, date_to)

        assert "0" in str(exc_info.value.message)

    def test_execute_employee_not_exists(self, use_case, mock_employee_gateway):
        """Test que verifica error cuando el empleado no existe."""
        # Arrange
        employee_id = 999
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)

        mock_employee_gateway.exists_by_id.return_value = False

        # Act & Assert
        with pytest.raises(EmployeeNotExistsError) as exc_info:
            use_case.execute(employee_id, date_from, date_to)

        assert "999" in str(exc_info.value.message)
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)

    def test_execute_invalid_date_range(self, use_case, mock_employee_gateway):
        """Test que verifica error cuando el rango de fechas es inválido."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 22)  # Fecha posterior
        date_to = date(2024, 1, 14)  # Fecha anterior

        mock_employee_gateway.exists_by_id.return_value = True

        # Act & Assert
        with pytest.raises(InvalidDateRangeError) as exc_info:
            use_case.execute(employee_id, date_from, date_to)

        assert "2024-01-22" in str(exc_info.value.message)
        assert "2024-01-14" in str(exc_info.value.message)

    def test_execute_gateway_error(self, use_case, mock_gateway, mock_employee_gateway):
        """Test que verifica el manejo de errores del gateway."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)

        mock_employee_gateway.exists_by_id.return_value = True
        mock_gateway.all.side_effect = Exception("Error de conexión")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(employee_id, date_from, date_to)

        assert "Error de conexión" in str(exc_info.value)

    def test_execute_with_different_employee_ids(
        self, use_case, mock_gateway, mock_employee_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución con diferentes employee_ids."""
        # Arrange
        employee_id = 2
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)

        mock_employee_gateway.exists_by_id.return_value = True
        mock_gateway.all.return_value = [
            sample_timesheet_lines[1]
        ]  # Solo el segundo timesheet

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_gateway.all.assert_called_once_with(employee_id, date_from, date_to)
        assert len(result) == 1
        assert result[0].employee_id == employee_id

    def test_execute_with_wide_date_range(
        self, use_case, mock_gateway, mock_employee_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución con un rango de fechas amplio."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 12, 31)

        mock_employee_gateway.exists_by_id.return_value = True
        mock_gateway.all.return_value = sample_timesheet_lines

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_gateway.all.assert_called_once_with(employee_id, date_from, date_to)
        assert result == sample_timesheet_lines
