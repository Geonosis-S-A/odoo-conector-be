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


class TestListTimesheetLinesUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=OdooTimesheetLineGateway)

    @pytest.fixture
    def use_case(self, mock_gateway):
        return ListTimesheetLinesUseCase(mock_gateway)

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

    def test_execute_without_filters(
        self, use_case, mock_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución sin filtros."""
        # Arrange
        mock_gateway.all.return_value = sample_timesheet_lines

        # Act
        result = use_case.execute()

        # Assert
        mock_gateway.all.assert_called_once_with(None, None, None)
        assert result == sample_timesheet_lines

    def test_execute_with_employee_filter(
        self, use_case, mock_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución con filtro de empleado."""
        # Arrange
        employee_id = 1
        mock_gateway.all.return_value = [
            sample_timesheet_lines[0]
        ]  # Solo el primer timesheet

        # Act
        result = use_case.execute(employee_id=employee_id)

        # Assert
        mock_gateway.all.assert_called_once_with(employee_id, None, None)
        assert len(result) == 1
        assert result[0].employee_id == employee_id

    def test_execute_with_date_range_filter(
        self, use_case, mock_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución con filtro de rango de fechas."""
        # Arrange
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 16)
        mock_gateway.all.return_value = [
            sample_timesheet_lines[0]
        ]  # Solo el primer timesheet

        # Act
        result = use_case.execute(date_from=date_from, date_to=date_to)

        # Assert
        mock_gateway.all.assert_called_once_with(None, date_from, date_to)
        assert len(result) == 1
        assert date_from <= result[0].date <= date_to

    def test_execute_with_date_from_only(
        self, use_case, mock_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución con solo fecha de inicio."""
        # Arrange
        date_from = date(2024, 1, 18)
        mock_gateway.all.return_value = [
            sample_timesheet_lines[1]
        ]  # Solo el segundo timesheet

        # Act
        result = use_case.execute(date_from=date_from)

        # Assert
        mock_gateway.all.assert_called_once_with(None, date_from, None)
        assert len(result) == 1
        assert result[0].date >= date_from

    def test_execute_with_date_to_only(
        self, use_case, mock_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución con solo fecha de fin."""
        # Arrange
        date_to = date(2024, 1, 16)
        mock_gateway.all.return_value = [
            sample_timesheet_lines[0]
        ]  # Solo el primer timesheet

        # Act
        result = use_case.execute(date_to=date_to)

        # Assert
        mock_gateway.all.assert_called_once_with(None, None, date_to)
        assert len(result) == 1
        assert result[0].date <= date_to

    def test_execute_with_all_filters(
        self, use_case, mock_gateway, sample_timesheet_lines
    ):
        """Test que verifica la ejecución con todos los filtros."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 16)
        mock_gateway.all.return_value = [sample_timesheet_lines[0]]

        # Act
        result = use_case.execute(
            employee_id=employee_id, date_from=date_from, date_to=date_to
        )

        # Assert
        mock_gateway.all.assert_called_once_with(employee_id, date_from, date_to)
        assert len(result) == 1
        assert result[0].employee_id == employee_id
        assert date_from <= result[0].date <= date_to

    def test_execute_returns_empty_list(self, use_case, mock_gateway):
        """Test que verifica que se retorna una lista vacía cuando no hay resultados."""
        # Arrange
        mock_gateway.all.return_value = []

        # Act
        result = use_case.execute()

        # Assert
        mock_gateway.all.assert_called_once_with(None, None, None)
        assert result == []
