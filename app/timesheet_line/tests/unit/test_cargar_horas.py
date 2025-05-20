from datetime import date
import pytest
from unittest.mock import Mock

from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.domain.repositories import TimesheetLineGateway


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

        # Act
        use_case.execute(request)

        # Assert
        mock_gateway.create.assert_called_once()
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

        # Act
        use_case.execute(request)

        # Assert
        mock_gateway.create.assert_called_once()
        created_timesheet = mock_gateway.create.call_args[0][0]
        assert created_timesheet.name == request.name
        assert created_timesheet.employee_id == request.employee_id
        assert created_timesheet.project_id == request.project_id
        assert created_timesheet.hours == request.hours
        assert created_timesheet.date == request.date
        assert created_timesheet.id is None
        assert created_timesheet.task_id == 123
