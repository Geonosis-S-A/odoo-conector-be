import pytest
from unittest.mock import Mock, AsyncMock
from datetime import date
from app.timesheet_line.application.use_cases.validar_timesheet import (
    ValidateTimesheetUseCase,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.users.domain.models import Employee
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetNotFoundError,
    TimesheetValidateError,
    ApproverNotFoundError,
)


class TestValidateTimesheetUseCase:
    @pytest.fixture
    def mock_gateway(self):
        """Fixture que proporciona un gateway mockeado."""
        return Mock()

    @pytest.fixture
    def mock_email_service(self):
        """Fixture que proporciona un servicio de email mockeado."""
        mock = AsyncMock()
        mock.send_approved_mail = AsyncMock()
        return mock

    @pytest.fixture
    def mock_employee_gateway(self):
        """Fixture que proporciona un gateway de empleados mockeado."""
        mock = Mock()
        # Mock por defecto para el approver
        mock.get_by_email.return_value = Employee(
            id=999, email="approver@test.com", full_name="Test Approver"
        )
        # Mock por defecto para empleados
        mock.get_by_id.return_value = Employee(
            id=1, email="employee@test.com", full_name="Test Employee"
        )
        return mock

    @pytest.fixture
    def mock_notification_repository(self):
        """Fixture que proporciona un repositorio de notificaciones mockeado."""
        return Mock()

    @pytest.fixture
    def use_case(
        self,
        mock_gateway,
        mock_email_service,
        mock_employee_gateway,
        mock_notification_repository,
    ):
        """Fixture que proporciona el caso de uso con todos los mocks necesarios."""
        return ValidateTimesheetUseCase(
            mock_gateway,
            mock_email_service,
            mock_employee_gateway,
            mock_notification_repository,
        )

    async def test_validate_single_timesheet_success(
        self, use_case, mock_gateway, mock_email_service, mock_employee_gateway
    ):
        """Test que verifica la validación exitosa de una línea de timesheet."""
        # Arrange
        timesheet_ids = [1]
        approver_mail = "approver@test.com"

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
        result = await use_case.execute(timesheet_ids, approver_mail)

        # Assert
        assert result is True
        mock_gateway.get_by_ids.assert_called_with([1])
        mock_gateway.validate.assert_called_once_with([1])
        mock_employee_gateway.get_by_email.assert_called_once_with(approver_mail)
        mock_email_service.send_approved_mail.assert_called_once()

    async def test_validate_multiple_timesheets_success(
        self, use_case, mock_gateway, mock_email_service, mock_employee_gateway
    ):
        """Test que verifica la validación exitosa de múltiples líneas de timesheet."""
        # Arrange
        timesheet_ids = [1, 2, 3]
        approver_mail = "approver@test.com"

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
        result = await use_case.execute(timesheet_ids, approver_mail)

        # Assert
        assert result is True
        mock_gateway.get_by_ids.assert_called_with([1, 2, 3])
        mock_gateway.validate.assert_called_once_with([1, 2, 3])
        mock_employee_gateway.get_by_email.assert_called_once_with(approver_mail)
        mock_email_service.send_approved_mail.assert_called_once()

    async def test_validate_timesheet_not_found_empty_list(
        self, use_case, mock_gateway
    ):
        """Test que verifica el error cuando no se encuentran las líneas a validar (lista vacía)."""
        # Arrange
        timesheet_ids = [999]  # ID inexistente
        approver_mail = "approver@test.com"

        # Mock de la respuesta del gateway - devuelve lista vacía
        mock_gateway.get_by_ids.return_value = []

        # Act & Assert
        with pytest.raises(
            TimesheetNotFoundError,
            match="No se encontraron las líneas de timesheet con IDs: \\[999\\]",
        ):
            await use_case.execute(timesheet_ids, approver_mail)

        # Verificar que se llamó a get_by_ids pero no a validate
        mock_gateway.get_by_ids.assert_called_once_with([999])
        mock_gateway.validate.assert_not_called()

    async def test_validate_timesheet_partial_not_found(self, use_case, mock_gateway):
        """Test que verifica el error cuando solo se encuentran algunas de las líneas a validar."""
        # Arrange
        timesheet_ids = [1, 999]  # Un ID válido y uno inexistente
        approver_mail = "approver@test.com"

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
            await use_case.execute(timesheet_ids, approver_mail)

        # Verificar que se llamó a get_by_ids pero no a validate
        mock_gateway.get_by_ids.assert_called_once_with([1, 999])
        mock_gateway.validate.assert_not_called()

    async def test_validate_timesheet_validate_fails(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando falla la validación."""
        # Arrange
        timesheet_ids = [1]
        approver_mail = "approver@test.com"

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
            await use_case.execute(timesheet_ids, approver_mail)

        mock_gateway.get_by_ids.assert_called_once_with([1])
        mock_gateway.validate.assert_called_once_with([1])

    async def test_validate_timesheet_validate_exception(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando validate lanza una excepción."""
        # Arrange
        timesheet_ids = [1]
        approver_mail = "approver@test.com"

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
            await use_case.execute(timesheet_ids, approver_mail)

        mock_gateway.get_by_ids.assert_called_once_with([1])
        mock_gateway.validate.assert_called_once_with([1])

    async def test_validate_empty_list(self, use_case, mock_gateway):
        """Test que verifica el comportamiento cuando se pasa una lista vacía de IDs."""
        # Arrange
        timesheet_ids = []
        approver_mail = "approver@test.com"

        # Mock de la respuesta del gateway
        mock_gateway.get_by_ids.return_value = []

        # Act & Assert
        with pytest.raises(
            TimesheetNotFoundError,
            match="No se encontraron las líneas de timesheet con IDs: \\[\\]",
        ):
            await use_case.execute(timesheet_ids, approver_mail)

        mock_gateway.get_by_ids.assert_called_once_with([])
        mock_gateway.validate.assert_not_called()

    async def test_validate_multiple_timesheets_with_exception_detail(
        self, use_case, mock_gateway
    ):
        """Test que verifica que el mensaje de error incluye los detalles de la excepción."""
        # Arrange
        timesheet_ids = [1, 2]
        approver_mail = "approver@test.com"

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
            await use_case.execute(timesheet_ids, approver_mail)

        # Verificar que el mensaje incluye el detalle de la excepción
        assert "No se pudo conectar con Odoo" in str(exc_info.value)
        assert "Error al validar las líneas de timesheet con IDs [1, 2]" in str(
            exc_info.value
        )

        mock_gateway.get_by_ids.assert_called_once_with([1, 2])
        mock_gateway.validate.assert_called_once_with([1, 2])

    async def test_validate_timesheet_approver_not_found(
        self, use_case, mock_gateway, mock_employee_gateway
    ):
        """Test que verifica el error cuando no se encuentra el approver."""
        # Arrange
        timesheet_ids = [1]
        approver_mail = "nonexistent@test.com"

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
        # Mock para que el approver no se encuentre
        mock_employee_gateway.get_by_email.return_value = None

        # Act & Assert
        with pytest.raises(
            ApproverNotFoundError,
            match="El empleado que intenta enviar el correo de revisión no existe: nonexistent@test.com",
        ):
            await use_case.execute(timesheet_ids, approver_mail)

        mock_gateway.get_by_ids.assert_called_once_with([1])
        mock_gateway.validate.assert_called_once_with([1])
        mock_employee_gateway.get_by_email.assert_called_once_with(approver_mail)
