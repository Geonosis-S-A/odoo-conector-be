from datetime import date
import pytest
from unittest.mock import Mock, patch

from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.application.use_cases.cargar_horas import CargarHorasUseCase
from app.timesheet_line.domain.repositories import TimesheetLineRepository


class TestCargarHorasUseCase:
    @pytest.fixture
    def mock_repository(self):
        return Mock(spec=TimesheetLineRepository)

    @pytest.fixture
    def use_case(self, mock_repository):
        return CargarHorasUseCase(mock_repository)

    def test_execute_creates_timesheet_line(self, use_case, mock_repository):
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
        mock_repository.create.assert_called_once()
        created_timesheet = mock_repository.create.call_args[0][0]
        assert created_timesheet.name == request.name
        assert created_timesheet.employee_id == request.employee_id
        assert created_timesheet.project_id == request.project_id
        assert created_timesheet.hours == request.hours
        assert created_timesheet.date == request.date
        assert created_timesheet.id is None
