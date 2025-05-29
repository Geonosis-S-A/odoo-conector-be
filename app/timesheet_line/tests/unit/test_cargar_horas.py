from datetime import date
import pytest
from unittest.mock import Mock

from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    InvalidHoursError,
    TimesheetCreationError,
    TimesheetNotFoundError,
)


class TestCargarHorasUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=TimesheetLineGateway)

    @pytest.fixture
    def use_case(self, mock_gateway):
        return CargarHorasUseCase(mock_gateway)

    def test_execute_creates_timesheet_line_without_task(self, use_case, mock_gateway):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
            )
        ]
        mock_gateway.create.return_value = [123]
        mock_gateway.get_by_ids.return_value = [Mock()]

        # Act
        result = use_case.execute(requests)

        # Assert
        mock_gateway.create.assert_called_once()
        mock_gateway.get_by_ids.assert_called_once_with([123])
        created_timesheet_lines = mock_gateway.create.call_args[0][0]
        assert len(created_timesheet_lines) == 1
        created_timesheet = created_timesheet_lines[0]
        assert created_timesheet.name == requests[0].name
        assert created_timesheet.employee_id == requests[0].employee_id
        assert created_timesheet.project_id == requests[0].project_id
        assert created_timesheet.hours == requests[0].hours
        assert created_timesheet.date == requests[0].date
        assert created_timesheet.id is None
        assert created_timesheet.task_id is None
        assert isinstance(result, list)
        assert len(result) == 1

    def test_execute_creates_timesheet_line_with_task(self, use_case, mock_gateway):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
                task_id=123,
            )
        ]
        mock_gateway.create.return_value = [456]
        mock_gateway.get_by_ids.return_value = [Mock()]

        # Act
        result = use_case.execute(requests)

        # Assert
        mock_gateway.create.assert_called_once()
        mock_gateway.get_by_ids.assert_called_once_with([456])
        created_timesheet_lines = mock_gateway.create.call_args[0][0]
        assert len(created_timesheet_lines) == 1
        created_timesheet = created_timesheet_lines[0]
        assert created_timesheet.name == requests[0].name
        assert created_timesheet.employee_id == requests[0].employee_id
        assert created_timesheet.project_id == requests[0].project_id
        assert created_timesheet.hours == requests[0].hours
        assert created_timesheet.date == requests[0].date
        assert created_timesheet.id is None
        assert created_timesheet.task_id == 123
        assert isinstance(result, list)
        assert len(result) == 1

    def test_execute_raises_invalid_hours_error_for_negative_hours(self, use_case):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=-1.0,  # Horas negativas
                date=date(2024, 1, 1),
            )
        ]

        # Act & Assert
        with pytest.raises(InvalidHoursError) as exc_info:
            use_case.execute(requests)

        assert "Las horas no pueden ser negativas" in str(exc_info.value.message)
        assert "-1.0" in str(exc_info.value.message)

    def test_execute_raises_timesheet_creation_error_when_create_fails(
        self, use_case, mock_gateway
    ):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
            )
        ]
        mock_gateway.create.return_value = None  # Simula fallo en creación

        # Act & Assert
        with pytest.raises(TimesheetCreationError):
            use_case.execute(requests)

    def test_execute_raises_timesheet_not_found_error_when_get_by_ids_fails(
        self, use_case, mock_gateway
    ):
        # Arrange
        requests = [
            CargarHorasRequest(
                name="Test Task",
                employee_id=1,
                project_id=1,
                hours=8.0,
                date=date(2024, 1, 1),
            )
        ]
        mock_gateway.create.return_value = [123]
        mock_gateway.get_by_ids.return_value = []  # Simula que no se encuentran las líneas creadas

        # Act & Assert
        with pytest.raises(TimesheetCreationError) as exc_info:
            use_case.execute(requests)

        assert "No se pudieron obtener las líneas de timesheet creadas" in str(
            exc_info.value.message
        )
