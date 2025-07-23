import pytest
from unittest.mock import Mock
from datetime import date
from app.timesheet_line.application.use_cases.edit_timesheet import EditTimesheetUseCase
from app.timesheet_line.api.schemas import EditTimesheetRequest
from app.timesheet_line.domain.models import DetailedTimesheetLine, TimesheetLine
from app.project.domain.models import Project
from app.timesheet_line.application.excepctions.exceptions import (
    InvalidHoursError,
    TimesheetNotFoundError,
    TimesheetEditError,
)


class TestEditTimesheetUseCase:
    @pytest.fixture
    def mock_gateway(self):
        """Fixture que proporciona un gateway mockeado."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_gateway):
        """Fixture que proporciona el caso de uso con el gateway mockeado."""
        return EditTimesheetUseCase(mock_gateway)

    def test_edit_timesheet_success(self, use_case, mock_gateway):
        """Test que verifica la edición exitosa de una línea de timesheet."""
        # Arrange
        request = EditTimesheetRequest(
            id=1,
            name="Test Timesheet",
            employee_id=1,
            project_id=1,
            hours=4.0,
            date=date(2024, 3, 20),
        )

        # Mock de la respuesta del gateway
        mock_gateway.get_by_id.return_value = DetailedTimesheetLine(
            id=1,
            name="Old Name",
            employee_id=1,
            project=Project(id=1, name="Test Project"),
            task=None,
            hours=8.0,
            date=date(2024, 3, 20),
            validated=False,
        )
        mock_gateway.update.return_value = True

        # Act
        result = use_case.execute(request)

        # Assert
        assert result is True
        mock_gateway.get_by_id.assert_called_once_with(1)
        mock_gateway.update.assert_called_once()

        # Verificar que se llamó a update con los datos correctos
        update_call_args = mock_gateway.update.call_args[0][0]
        assert isinstance(update_call_args, TimesheetLine)
        assert update_call_args.id == 1
        assert update_call_args.name == "Test Timesheet"
        assert update_call_args.hours == 4.0

    def test_edit_timesheet_negative_hours(self, use_case):
        """Test que verifica que no se pueden editar horas negativas."""
        # Arrange
        request = EditTimesheetRequest(
            id=1,
            name="Test Timesheet",
            employee_id=1,
            project_id=1,
            hours=-1.0,  # Horas negativas
            date=date(2024, 3, 20),
        )

        # Act & Assert
        with pytest.raises(
            InvalidHoursError, match="Las horas no pueden ser negativas"
        ):
            use_case.execute(request)

    def test_edit_timesheet_not_found(self, use_case, mock_gateway):
        """Test que verifica el error cuando no se encuentra la línea a editar."""
        # Arrange
        request = EditTimesheetRequest(
            id=999,  # ID inexistente
            name="Test Timesheet",
            employee_id=1,
            project_id=1,
            hours=4.0,
            date=date(2024, 3, 20),
        )

        # Mock de la respuesta del gateway - ahora devuelve None en lugar de lanzar excepción
        mock_gateway.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(
            TimesheetNotFoundError,
            match="No se encontraron las líneas de timesheet con IDs: \\[999\\]",
        ):
            use_case.execute(request)

    def test_edit_timesheet_update_fails(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando falla la actualización."""
        # Arrange
        request = EditTimesheetRequest(
            id=1,
            name="Test Timesheet",
            employee_id=1,
            project_id=1,
            hours=4.0,
            date=date(2024, 3, 20),
        )

        # Mock de la respuesta del gateway
        mock_gateway.get_by_id.return_value = DetailedTimesheetLine(
            id=1,
            name="Old Name",
            employee_id=1,
            project=Project(id=1, name="Test Project"),
            task=None,
            hours=8.0,
            date=date(2024, 3, 20),
            validated=False,
        )
        mock_gateway.update.return_value = False

        # Act & Assert
        with pytest.raises(
            TimesheetEditError, match="Error al editar la línea de timesheet con ID 1"
        ):
            use_case.execute(request)

        mock_gateway.get_by_id.assert_called_once_with(1)
        mock_gateway.update.assert_called_once()

    def test_edit_timesheet_update_exception(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando update lanza una excepción."""
        # Arrange
        request = EditTimesheetRequest(
            id=1,
            name="Test Timesheet",
            employee_id=1,
            project_id=1,
            hours=4.0,
            date=date(2024, 3, 20),
        )

        # Mock de la respuesta del gateway
        mock_gateway.get_by_id.return_value = DetailedTimesheetLine(
            id=1,
            name="Old Name",
            employee_id=1,
            project=Project(id=1, name="Test Project"),
            task=None,
            hours=8.0,
            date=date(2024, 3, 20),
            validated=False,
        )
        mock_gateway.update.side_effect = ValueError("ID requerido")

        # Act & Assert
        with pytest.raises(
            TimesheetEditError, match="Error al editar la línea de timesheet con ID 1"
        ):
            use_case.execute(request)

        mock_gateway.get_by_id.assert_called_once_with(1)
        mock_gateway.update.assert_called_once()
