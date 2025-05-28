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
        request = CargarHorasRequest(
            name="Test Task",
            employee_id=1,
            project_id=1,
            hours=8.0,
            date=date(2024, 1, 1),
        )
        mock_gateway.create.return_value = 123
        mock_gateway.get_by_id.return_value = Mock()

        # Act
        use_case.execute(request)

        # Assert
        mock_gateway.create.assert_called_once()
        mock_gateway.get_by_id.assert_called_once_with(123)
        created_timesheet = mock_gateway.create.call_args[0][0]
        assert created_timesheet.name == request.name
        assert created_timesheet.employee_id == request.employee_id
        assert created_timesheet.project_id == request.project_id
        assert created_timesheet.hours == request.hours
        assert created_timesheet.date == request.date
        assert created_timesheet.id is None
        assert created_timesheet.task_id is None

    def test_execute_creates_timesheet_line_with_task(self, use_case, mock_gateway):
        # Arrange
        request = CargarHorasRequest(
            name="Test Task",
            employee_id=1,
            project_id=1,
            hours=8.0,
            date=date(2024, 1, 1),
            task_id=123,
        )
        mock_gateway.create.return_value = 456
        mock_gateway.get_by_id.return_value = Mock()

        # Act
        use_case.execute(request)

        # Assert
        mock_gateway.create.assert_called_once()
        mock_gateway.get_by_id.assert_called_once_with(456)
        created_timesheet = mock_gateway.create.call_args[0][0]
        assert created_timesheet.name == request.name
        assert created_timesheet.employee_id == request.employee_id
        assert created_timesheet.project_id == request.project_id
        assert created_timesheet.hours == request.hours
        assert created_timesheet.date == request.date
        assert created_timesheet.id is None
        assert created_timesheet.task_id == 123

    def test_execute_raises_invalid_hours_error_for_negative_hours(self, use_case):
        # Arrange
        request = CargarHorasRequest(
            name="Test Task",
            employee_id=1,
            project_id=1,
            hours=-1.0,  # Horas negativas
            date=date(2024, 1, 1),
        )

        # Act & Assert
        with pytest.raises(InvalidHoursError) as exc_info:
            use_case.execute(request)

        assert "Las horas no pueden ser negativas" in str(exc_info.value.message)
        assert "-1.0" in str(exc_info.value.message)

    def test_execute_raises_timesheet_creation_error_when_create_fails(
        self, use_case, mock_gateway
    ):
        # Arrange
        request = CargarHorasRequest(
            name="Test Task",
            employee_id=1,
            project_id=1,
            hours=8.0,
            date=date(2024, 1, 1),
        )
        mock_gateway.create.return_value = None  # Simula fallo en creación

        # Act & Assert
        with pytest.raises(TimesheetCreationError):
            use_case.execute(request)

    def test_execute_raises_timesheet_not_found_error_when_get_by_id_fails(
        self, use_case, mock_gateway
    ):
        # Arrange
        request = CargarHorasRequest(
            name="Test Task",
            employee_id=1,
            project_id=1,
            hours=8.0,
            date=date(2024, 1, 1),
        )
        mock_gateway.create.return_value = 123
        mock_gateway.get_by_id.return_value = None  # Simula que no se encuentra

        # Act & Assert
        with pytest.raises(TimesheetNotFoundError) as exc_info:
            use_case.execute(request)

        assert "123" in str(exc_info.value.message)
