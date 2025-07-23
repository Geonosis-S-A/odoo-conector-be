import pytest
from unittest.mock import Mock
from datetime import date
from app.timesheet_line.application.use_cases.validar_timesheet import (
    ValidateTimesheetUseCase,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetNotFoundError,
    TimesheetValidateError,
)


class TestValidateTimesheetUseCase:
    @pytest.fixture
    def mock_gateway(self):
        """Fixture que proporciona un gateway mockeado."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_gateway):
        """Fixture que proporciona el caso de uso con el gateway mockeado."""
        return ValidateTimesheetUseCase(mock_gateway)

    def test_validate_single_timesheet_success(self, use_case, mock_gateway):
        """Test que verifica la validación exitosa de una línea de timesheet."""
        # Arrange
        timesheet_ids = [1]

        # Mock de la respuesta del gateway
        mock_gateway.get_by_ids.return_value = [
            DetailedTimesheetLine(
                id=1,
                name="Test Timesheet",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 3, 20),
                validated=False,
            )
        ]
        mock_gateway.validate.return_value = True

        # Act
        result = use_case.execute(timesheet_ids)

        # Assert
        assert result is True
        mock_gateway.get_by_ids.assert_called_once_with([1])
        mock_gateway.validate.assert_called_once_with([1])

    def test_validate_multiple_timesheets_success(self, use_case, mock_gateway):
        """Test que verifica la validación exitosa de múltiples líneas de timesheet."""
        # Arrange
        timesheet_ids = [1, 2, 3]

        # Mock de la respuesta del gateway
        mock_gateway.get_by_ids.return_value = [
            DetailedTimesheetLine(
                id=1,
                name="Test Timesheet 1",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 3, 20),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=2,
                name="Test Timesheet 2",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=4.0,
                date=date(2024, 3, 21),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=3,
                name="Test Timesheet 3",
                employee_id=1,
                project=Project(id=2, name="Test Project 2"),
                task=None,
                hours=6.0,
                date=date(2024, 3, 22),
                validated=False,
            ),
        ]
        mock_gateway.validate.return_value = True

        # Act
        result = use_case.execute(timesheet_ids)

        # Assert
        assert result is True
        mock_gateway.get_by_ids.assert_called_once_with([1, 2, 3])
        mock_gateway.validate.assert_called_once_with([1, 2, 3])

    def test_validate_timesheet_not_found_empty_list(self, use_case, mock_gateway):
        """Test que verifica el error cuando no se encuentran las líneas a validar (lista vacía)."""
        # Arrange
        timesheet_ids = [999]  # ID inexistente

        # Mock de la respuesta del gateway - devuelve lista vacía
        mock_gateway.get_by_ids.return_value = []

        # Act & Assert
        with pytest.raises(
            TimesheetNotFoundError,
            match="No se encontraron las líneas de timesheet con IDs: \\[999\\]",
        ):
            use_case.execute(timesheet_ids)

        # Verificar que se llamó a get_by_ids pero no a validate
        mock_gateway.get_by_ids.assert_called_once_with([999])
        mock_gateway.validate.assert_not_called()

    def test_validate_timesheet_partial_not_found(self, use_case, mock_gateway):
        """Test que verifica el error cuando solo se encuentran algunas de las líneas a validar."""
        # Arrange
        timesheet_ids = [1, 999]  # Un ID válido y uno inexistente

        # Mock de la respuesta del gateway - solo devuelve una línea
        mock_gateway.get_by_ids.return_value = [
            DetailedTimesheetLine(
                id=1,
                name="Test Timesheet",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 3, 20),
                validated=False,
            )
        ]

        # Act & Assert
        with pytest.raises(
            TimesheetNotFoundError,
            match="No se encontraron las líneas de timesheet con IDs: \\[1, 999\\]",
        ):
            use_case.execute(timesheet_ids)

        # Verificar que se llamó a get_by_ids pero no a validate
        mock_gateway.get_by_ids.assert_called_once_with([1, 999])
        mock_gateway.validate.assert_not_called()

    def test_validate_timesheet_validate_fails(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando falla la validación."""
        # Arrange
        timesheet_ids = [1]

        # Mock de la respuesta del gateway
        mock_gateway.get_by_ids.return_value = [
            DetailedTimesheetLine(
                id=1,
                name="Test Timesheet",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 3, 20),
                validated=False,
            )
        ]
        mock_gateway.validate.return_value = False

        # Act & Assert
        with pytest.raises(
            TimesheetValidateError,
            match="Error al validar las líneas de timesheet con IDs \\[1\\]",
        ):
            use_case.execute(timesheet_ids)

        mock_gateway.get_by_ids.assert_called_once_with([1])
        mock_gateway.validate.assert_called_once_with([1])

    def test_validate_timesheet_validate_exception(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando validate lanza una excepción."""
        # Arrange
        timesheet_ids = [1]

        # Mock de la respuesta del gateway
        mock_gateway.get_by_ids.return_value = [
            DetailedTimesheetLine(
                id=1,
                name="Test Timesheet",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 3, 20),
                validated=False,
            )
        ]
        mock_gateway.validate.side_effect = ValueError("Error de conexión")

        # Act & Assert
        with pytest.raises(
            TimesheetValidateError,
            match="Error al validar las líneas de timesheet con IDs \\[1\\]",
        ):
            use_case.execute(timesheet_ids)

        mock_gateway.get_by_ids.assert_called_once_with([1])
        mock_gateway.validate.assert_called_once_with([1])

    def test_validate_empty_list(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando se pasa una lista vacía de IDs."""
        # Arrange
        timesheet_ids = []

        # Mock de la respuesta del gateway
        mock_gateway.get_by_ids.return_value = []

        # Act & Assert
        with pytest.raises(
            TimesheetNotFoundError,
            match="No se encontraron las líneas de timesheet con IDs: \\[\\]",
        ):
            use_case.execute(timesheet_ids)

        mock_gateway.get_by_ids.assert_called_once_with([])
        mock_gateway.validate.assert_not_called()

    def test_validate_multiple_timesheets_with_exception_detail(
        self, use_case, mock_gateway
    ):
        """Test que verifica que el mensaje de error incluye los detalles de la excepción."""
        # Arrange
        timesheet_ids = [1, 2]

        # Mock de la respuesta del gateway
        mock_gateway.get_by_ids.return_value = [
            DetailedTimesheetLine(
                id=1,
                name="Test Timesheet 1",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 3, 20),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=2,
                name="Test Timesheet 2",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=4.0,
                date=date(2024, 3, 21),
                validated=False,
            ),
        ]
        mock_gateway.validate.side_effect = ConnectionError(
            "No se pudo conectar con Odoo"
        )

        # Act & Assert
        with pytest.raises(TimesheetValidateError) as exc_info:
            use_case.execute(timesheet_ids)

        # Verificar que el mensaje incluye el detalle de la excepción
        assert "No se pudo conectar con Odoo" in str(exc_info.value)
        assert "Error al validar las líneas de timesheet con IDs [1, 2]" in str(
            exc_info.value
        )

        mock_gateway.get_by_ids.assert_called_once_with([1, 2])
        mock_gateway.validate.assert_called_once_with([1, 2])
