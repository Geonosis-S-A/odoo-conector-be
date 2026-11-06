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
        mock.get_by_ids.side_effect = lambda ids: [
            Employee(id=i, email="employee@test.com", full_name="Test Employee")
            for i in ids
        ]
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

    @staticmethod
    def _line(line_id: int, validated: bool) -> DetailedTimesheetLine:
        return DetailedTimesheetLine(
            id=line_id,
            name="Test Timesheet",
            employee_id=1,
            project=Project(id=1, name="Test Project"),
            task=None,
            hours=8.0,
            date=date(2024, 3, 20),
            validated=validated,
        )

    async def test_already_validated_lines_are_skipped_without_error(
        self, use_case, mock_gateway, mock_email_service
    ):
        """Si otro aprobador (PM o gerente) ya validó todo, no se vuelve a
        validar, no se pisa x_validated_by ni se reenvía el mail."""
        mock_gateway.get_by_ids.return_value = [self._line(1, True), self._line(2, True)]

        result = await use_case.execute([1, 2], "approver@test.com")

        assert result is True
        mock_gateway.validate.assert_not_called()
        mock_email_service.send_approved_mail.assert_not_called()

    async def test_only_pending_lines_are_validated_when_some_already_validated(
        self, use_case, mock_gateway
    ):
        mock_gateway.get_by_ids.side_effect = [
            [self._line(1, True), self._line(2, False)],
            [self._line(2, True)],
        ]
        mock_gateway.validate.return_value = True

        result = await use_case.execute([1, 2], "approver@test.com")

        assert result is True
        mock_gateway.validate.assert_called_once_with([2], 999)

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
        mock_gateway.validate.assert_called_once_with([1], 999)
        mock_employee_gateway.get_by_email.assert_called_once_with(approver_mail)
        mock_email_service.send_approved_mail.assert_called_once()

    async def test_validate_uses_validator_employee_id_when_provided(
        self, use_case, mock_gateway, mock_employee_gateway
    ):
        """El id enviado a Odoo debe ser el del usuario Geo que ejecuta la acción,
        no el del approver resuelto por email."""
        # Arrange
        timesheet_ids = [1]
        approver_mail = "approver@test.com"
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
        await use_case.execute(
            timesheet_ids, approver_mail, validator_employee_id=42
        )

        # Assert
        mock_gateway.validate.assert_called_once_with([1], 42)

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
        mock_gateway.validate.assert_called_once_with([1, 2, 3], 999)
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
        mock_gateway.validate.assert_called_once_with([1], 999)

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
        mock_gateway.validate.assert_called_once_with([1], 999)

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

    async def test_employees_are_resolved_in_a_single_call(
        self, use_case, mock_gateway, mock_employee_gateway
    ):
        """Al armar los mails se consultan los empleados una sola vez, no una
        por línea."""
        lines = []
        for line_id, employee_id in [(1, 1), (2, 1), (3, 2)]:
            lines.append(
                DetailedTimesheetLine(
                    id=line_id,
                    name="T",
                    employee_id=employee_id,
                    project=Project(id=1, name="P"),
                    task=None,
                    hours=8.0,
                    date=date(2024, 3, 20),
                    validated=False,
                )
            )
        mock_gateway.get_by_ids.return_value = lines
        mock_gateway.validate.return_value = True

        await use_case.execute([1, 2, 3], "approver@test.com")

        mock_employee_gateway.get_by_ids.assert_called_once()
        (called_ids,) = mock_employee_gateway.get_by_ids.call_args[0]
        assert sorted(called_ids) == [1, 2]

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
        mock_gateway.validate.assert_called_once_with([1, 2], 999)

    async def test_non_admin_cannot_validate_outside_validatable_team(
        self, mock_gateway, mock_email_service, mock_employee_gateway,
        mock_notification_repository,
    ):
        """Un no-admin no puede validar líneas de proyectos que no gerencia."""
        team_access = Mock()
        team_access.lines_authority.return_value = {(7, 1): False}
        use_case = ValidateTimesheetUseCase(
            mock_gateway, mock_email_service, mock_employee_gateway,
            mock_notification_repository, team_access,
        )
        mock_gateway.get_by_ids.return_value = [
            DetailedTimesheetLine(
                id=1, name="ts", employee_id=7,
                project=Project(id=1, name="P"), task=None, hours=8.0,
                date=date(2024, 3, 20), validated=False,
            )
        ]

        with pytest.raises(TimesheetValidateError, match="no gerenciás su proyecto"):
            await use_case.execute(
                [1], "approver@test.com", validator_employee_id=5
            )
        mock_gateway.validate.assert_not_called()
        team_access.lines_authority.assert_called_once_with(5, [(7, 1)])

    async def test_non_admin_validates_within_validatable_team(
        self, mock_gateway, mock_email_service, mock_employee_gateway,
        mock_notification_repository,
    ):
        """Un no-admin sí puede validar líneas de proyectos que gerencia."""
        team_access = Mock()
        team_access.lines_authority.return_value = {(7, 1): True}
        use_case = ValidateTimesheetUseCase(
            mock_gateway, mock_email_service, mock_employee_gateway,
            mock_notification_repository, team_access,
        )
        mock_gateway.get_by_ids.return_value = [
            DetailedTimesheetLine(
                id=1, name="ts", employee_id=7,
                project=Project(id=1, name="P"), task=None, hours=8.0,
                date=date(2024, 3, 20), validated=False,
            )
        ]
        mock_gateway.validate.return_value = True

        result = await use_case.execute(
            [1], "approver@test.com", validator_employee_id=5
        )

        assert result is True
        mock_gateway.validate.assert_called_once_with([1], 5)

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
        # Mock para que el approver no se encuentre
        mock_employee_gateway.get_by_email.return_value = None

        # Act & Assert
        with pytest.raises(
            ApproverNotFoundError,
            match="El empleado que intenta enviar el correo de revisión no existe: nonexistent@test.com",
        ):
            await use_case.execute(timesheet_ids, approver_mail)

        # El approver se verifica antes de validar en Odoo
        mock_gateway.get_by_ids.assert_called_once_with([1])
        mock_gateway.validate.assert_not_called()
        mock_employee_gateway.get_by_email.assert_called_once_with(approver_mail)
