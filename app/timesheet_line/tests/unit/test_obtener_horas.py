from datetime import date, datetime
import pytest
from unittest.mock import Mock

from app.timesheet_line.application.use_cases.obtener_horas import (
    ListTimesheetLinesUseCase,
)
from app.timesheet_line.domain.models import (
    DetailedTimesheetLine,
    TimesheetLineNotification,
)
from app.timesheet_line.domain.repositories import TimesheetLineNotificationRepository
from app.timesheet_line.api.schemas import TimesheetLineNotificationResponse
from app.project.domain.models import Project
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway
from app.users.domain.models import Employee
from app.timesheet_line.application.excepctions.exceptions import (
    InvalidEmployeeIdError,
    EmployeeNotExistsError,
    InvalidDateRangeError,
    TimesheetListError,
    EmployeeNotHasUserError,
)


class TestListTimesheetLinesUseCase:
    @pytest.fixture
    def mock_gateway(self):
        return Mock(spec=TimesheetLineGateway)

    @pytest.fixture
    def mock_employee_gateway(self):
        return Mock(spec=EmployeeGateway)

    @pytest.fixture
    def mock_notification_repository(self):
        return Mock(spec=TimesheetLineNotificationRepository)

    @pytest.fixture
    def sample_employees(self):
        return [
            Employee(id=1, full_name="John Doe", email="john@example.com"),
            Employee(id=2, full_name="Jane Smith", email="jane@example.com"),
            Employee(id=3, full_name="Bob Johnson", email="bob@example.com"),
        ]

    @pytest.fixture
    def sample_notification(self):
        return TimesheetLineNotification(
            id=1,
            timesheet_line_id=1,
            approver_id=2,
            receiver_id=1,
            created_at=datetime(2024, 1, 16, 10, 30, 0),
        )

    @pytest.fixture
    def use_case(
        self, mock_gateway, mock_employee_gateway, mock_notification_repository
    ):
        return ListTimesheetLinesUseCase(
            mock_gateway, mock_employee_gateway, mock_notification_repository
        )

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
                validated=False,
            ),
            DetailedTimesheetLine(
                id=2,
                name="Test Timesheet 2",
                employee_id=2,
                project=Project(id=2, name="Test Project 2"),
                task=None,
                hours=4.0,
                date=date(2024, 1, 20),
                validated=False,
            ),
        ]

    def test_execute_success_with_required_params(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica la ejecución exitosa con parámetros obligatorios."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        uid = 1
        user_id = 123  # ID del usuario obtenido desde el employee_id

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = sample_timesheet_lines
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, True, uid
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_employee_gateway.get_user_id_by_employee_id.assert_called_once_with(uid)
        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, None, True, user_id
        )
        # Verificar que se buscó notificación para cada timesheet
        assert mock_notification_repository.get_by_timesheet_id.call_count == len(
            sample_timesheet_lines
        )
        assert result == sample_timesheet_lines
        # Verificar que notification es None en todos los timesheets
        for timesheet in result:
            assert timesheet.notification is None

    def test_execute_returns_empty_list_when_no_results(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica que se devuelve una lista vacía cuando no hay resultados."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        uid = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = []  # Sin resultados

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, True, uid
        )

        # Assert
        assert result == []
        assert isinstance(result, list)
        assert len(result) == 0
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_employee_gateway.get_user_id_by_employee_id.assert_called_once_with(uid)
        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, None, True, user_id
        )
        # No se debe llamar get_by_timesheet_id si no hay resultados
        mock_notification_repository.get_by_timesheet_id.assert_not_called()

    def test_execute_with_specific_employee_and_date_range(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica la ejecución con empleado específico y rango de fechas."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 16)
        uid = 1

        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = [
            sample_timesheet_lines[0]
        ]  # Solo el primer timesheet
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, True, uid
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_employee_gateway.get_user_id_by_employee_id.assert_called_once_with(uid)
        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, None, True, user_id
        )
        mock_notification_repository.get_by_timesheet_id.assert_called_once_with(1)
        assert len(result) == 1
        assert result[0].employee_id == employee_id
        assert date_from <= result[0].date <= date_to
        assert result[0].notification is None

    # TESTS PARA VALIDACIONES
    def test_execute_invalid_employee_id_negative(self, use_case):
        """Test que verifica error con employee_id negativo."""
        # Arrange
        employee_id = -1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        uid = 1

        # Act & Assert
        with pytest.raises(InvalidEmployeeIdError) as exc_info:
            use_case.execute(employee_id, date_from, date_to, None, None, False, uid)

        assert "-1" in str(exc_info.value.message)

    def test_execute_invalid_employee_id_zero(self, use_case):
        """Test que verifica error con employee_id cero."""
        # Arrange
        employee_id = 0
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        uid = 1

        # Act & Assert
        with pytest.raises(InvalidEmployeeIdError) as exc_info:
            use_case.execute(employee_id, date_from, date_to, None, None, False, uid)

        assert "0" in str(exc_info.value.message)

    def test_execute_employee_not_exists(self, use_case, mock_employee_gateway):
        """Test que verifica error cuando el empleado no existe."""
        # Arrange
        employee_id = 999
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        uid = 1

        mock_employee_gateway.exists_by_id.return_value = False

        # Act & Assert
        with pytest.raises(EmployeeNotExistsError) as exc_info:
            use_case.execute(employee_id, date_from, date_to, None, None, False, uid)

        assert "999" in str(exc_info.value.message)
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)

    def test_execute_invalid_date_range(self, use_case, mock_employee_gateway):
        """Test que verifica error cuando el rango de fechas es inválido."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 22)  # Fecha posterior
        date_to = date(2024, 1, 14)  # Fecha anterior
        uid = 1

        mock_employee_gateway.exists_by_id.return_value = True

        # Act & Assert
        with pytest.raises(InvalidDateRangeError) as exc_info:
            use_case.execute(employee_id, date_from, date_to, None, None, False, uid)

        assert "2024-01-22" in str(exc_info.value.message)
        assert "2024-01-14" in str(exc_info.value.message)

    def test_execute_gateway_error(
        self, use_case, mock_gateway, mock_employee_gateway, sample_employees
    ):
        """Test que verifica el manejo de errores del gateway."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        uid = 1

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.side_effect = Exception("Error de conexión")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(employee_id, date_from, date_to, None, None, False, uid)

        assert "Error de conexión" in str(exc_info.value)

    def test_execute_with_different_employee_ids(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica la ejecución con diferentes employee_ids."""
        # Arrange
        employee_id = 2
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        uid = 1

        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = [
            sample_timesheet_lines[1]
        ]  # Solo el segundo timesheet
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, True, uid
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_employee_gateway.get_user_id_by_employee_id.assert_called_once_with(uid)
        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, None, True, user_id
        )
        mock_notification_repository.get_by_timesheet_id.assert_called_once_with(2)
        assert len(result) == 1
        assert result[0].employee_id == employee_id

    def test_execute_with_wide_date_range(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica la ejecución con un rango de fechas amplio."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 12, 31)
        uid = 1

        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = sample_timesheet_lines
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, False, uid
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        # No debe llamar get_user_id_by_employee_id cuando team=False
        mock_employee_gateway.get_user_id_by_employee_id.assert_not_called()
        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, None, False, None
        )
        assert mock_notification_repository.get_by_timesheet_id.call_count == len(
            sample_timesheet_lines
        )
        assert result == sample_timesheet_lines

    # TESTS PARA FILTRO POR PROJECT_ID
    def test_execute_with_project_id_filter(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica el filtrado por project_id."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        project_id = 1
        uid = 1

        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        # Solo devolver timesheets del proyecto 1
        filtered_timesheets = [
            ts for ts in sample_timesheet_lines if ts.project.id == project_id
        ]
        mock_gateway.all.return_value = filtered_timesheets
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, project_id, None, False, uid
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        # No debe llamar get_user_id_by_employee_id cuando team=False
        mock_employee_gateway.get_user_id_by_employee_id.assert_not_called()
        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, project_id, None, False, None
        )
        assert mock_notification_repository.get_by_timesheet_id.call_count == len(
            filtered_timesheets
        )
        assert result == filtered_timesheets
        # Verificar que todos los resultados son del proyecto correcto
        for timesheet in result:
            assert timesheet.project.id == project_id

    def test_execute_with_project_id_zero(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica el comportamiento con project_id=0."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        project_id = 0
        uid = 1

        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = []

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, project_id, None, False, uid
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)

        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, project_id, None, False, None
        )
        mock_notification_repository.get_by_timesheet_id.assert_not_called()
        assert result == []

    # TESTS PARA FILTRO POR VALIDATED
    def test_execute_with_validated_true_filter(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica el filtrado por validated=True."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        validated = True
        id = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        # Crear timesheets validados
        validated_timesheets = [
            DetailedTimesheetLine(
                id=1,
                name="Validated Timesheet",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 1, 15),
                validated=True,
            )
        ]
        mock_gateway.all.return_value = validated_timesheets
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, validated, False, id
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)
        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, validated, False, None
        )
        mock_notification_repository.get_by_timesheet_id.assert_called_once_with(1)
        assert result == validated_timesheets
        # Verificar que todos los resultados están validados
        for timesheet in result:
            assert timesheet.validated is True

    def test_execute_with_validated_false_filter(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica el filtrado por validated=False."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        validated = False
        id = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        # Los sample_timesheet_lines ya tienen validated=False
        mock_gateway.all.return_value = sample_timesheet_lines
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, validated, False, id
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)

        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, validated, False, None
        )
        assert mock_notification_repository.get_by_timesheet_id.call_count == len(
            sample_timesheet_lines
        )
        assert result == sample_timesheet_lines
        # Verificar que todos los resultados no están validados
        for timesheet in result:
            assert timesheet.validated is False

    # TESTS PARA COMBINACIONES DE FILTROS
    def test_execute_with_all_filters(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica el uso de todos los filtros juntos."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        project_id = 1
        validated = True
        id = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        # Timesheet que cumple todos los criterios
        specific_timesheet = [
            DetailedTimesheetLine(
                id=1,
                name="Specific Timesheet",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 1, 15),
                validated=True,
            )
        ]
        mock_gateway.all.return_value = specific_timesheet
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, project_id, validated, False, id
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)

        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, project_id, validated, False, None
        )
        mock_notification_repository.get_by_timesheet_id.assert_called_once_with(1)
        assert result == specific_timesheet

    def test_execute_with_project_and_validated_filters(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica la combinación de filtros project_id y validated."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        project_id = 2
        validated = False
        id = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        # Timesheet del proyecto 2, no validado
        filtered_timesheet = [
            DetailedTimesheetLine(
                id=2,
                name="Project 2 Timesheet",
                employee_id=1,
                project=Project(id=2, name="Test Project 2"),
                task=None,
                hours=4.0,
                date=date(2024, 1, 20),
                validated=False,
            )
        ]
        mock_gateway.all.return_value = filtered_timesheet
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, project_id, validated, False, id
        )

        # Assert
        mock_employee_gateway.exists_by_id.assert_called_once_with(employee_id)

        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, project_id, validated, False, None
        )
        mock_notification_repository.get_by_timesheet_id.assert_called_once_with(2)
        assert result == filtered_timesheet

    # TESTS SIN EMPLOYEE_ID (CASOS ADMIN)
    def test_execute_without_employee_id_with_filters(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica la ejecución sin employee_id pero con otros filtros (caso admin)."""
        # Arrange
        employee_id = None  # Admin puede ver todos
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        project_id = 1
        validated = False
        id = 1
        user_id = 123

        # No se valida employee_id cuando es None
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = sample_timesheet_lines
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, project_id, validated, False, id
        )

        # Assert
        # No debe llamar a exists_by_id cuando employee_id es None
        mock_employee_gateway.exists_by_id.assert_not_called()

        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, project_id, validated, False, None
        )
        assert mock_notification_repository.get_by_timesheet_id.call_count == len(
            sample_timesheet_lines
        )
        assert result == sample_timesheet_lines

    # TESTS ESPECÍFICOS PARA NOTIFICACIONES
    def test_execute_with_timesheet_with_notification(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
        sample_notification,
    ):
        """Test que verifica que se asignan correctamente las notificaciones a los timesheets."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        id = 1

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = [
            sample_timesheet_lines[0]
        ]  # Solo el primer timesheet
        mock_notification_repository.get_by_timesheet_id.return_value = (
            sample_notification
        )

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, False, id
        )

        # Assert
        mock_notification_repository.get_by_timesheet_id.assert_called_once_with(1)
        assert len(result) == 1
        timesheet = result[0]
        assert timesheet.notification is not None
        assert timesheet.notification.id == sample_notification.id
        assert timesheet.notification.sender_name == "Jane Smith"  # Employee id=2
        assert timesheet.notification.sended_at == sample_notification.created_at

    def test_execute_with_mixed_notifications(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
        sample_notification,
    ):
        """Test que verifica el comportamiento cuando algunos timesheets tienen notificaciones y otros no."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        id = 1

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = sample_timesheet_lines

        # Solo el primer timesheet tiene notificación
        def get_notification_side_effect(timesheet_id):
            if timesheet_id == 1:
                return sample_notification
            return None

        mock_notification_repository.get_by_timesheet_id.side_effect = (
            get_notification_side_effect
        )

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, False, id
        )

        # Assert
        assert len(result) == 2
        # Primer timesheet debe tener notificación
        assert result[0].notification is not None
        assert result[0].notification.id == sample_notification.id
        # Segundo timesheet no debe tener notificación
        assert result[1].notification is None

    def test_execute_notification_with_missing_employee(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_notification,
    ):
        """Test que verifica el comportamiento cuando un empleado referenciado en la notificación no existe."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        id = 1

        # Solo incluir empleados que no incluyan el approver_id de la notificación
        limited_employees = [
            Employee(id=1, full_name="John Doe", email="john@example.com"),
            Employee(id=3, full_name="Bob Johnson", email="bob@example.com"),
        ]

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.all.return_value = limited_employees
        mock_gateway.all.return_value = [
            sample_timesheet_lines[0]
        ]  # Solo el primer timesheet
        mock_notification_repository.get_by_timesheet_id.return_value = (
            sample_notification
        )

        # Act & Assert - Esto debería generar un KeyError cuando trata de acceder al empleado id=2
        with pytest.raises(KeyError):
            use_case.execute(employee_id, date_from, date_to, None, None, False, id)

    def test_execute_performance_with_many_timesheets(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica que se llama get_by_timesheet_id para cada timesheet."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        id = 1

        # Crear varios timesheets
        many_timesheets = []
        for i in range(5):
            timesheet = DetailedTimesheetLine(
                id=i + 1,
                name=f"Timesheet {i + 1}",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=date(2024, 1, 15 + i),
                validated=False,
            )
            many_timesheets.append(timesheet)

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = many_timesheets
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, False, id
        )

        # Assert
        assert len(result) == 5
        # Debe llamar get_by_timesheet_id una vez por cada timesheet
        assert mock_notification_repository.get_by_timesheet_id.call_count == 5
        # Verificar que se llamó con cada ID de timesheet
        expected_calls = [(i + 1,) for i in range(5)]
        actual_calls = [
            call.args
            for call in mock_notification_repository.get_by_timesheet_id.call_args_list
        ]
        assert actual_calls == expected_calls

    # TESTS ADICIONALES PARA CASOS EDGE Y VALIDACIONES
    def test_execute_with_date_from_none_and_date_to_valid(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica que date_from=None con date_to válido es permitido."""
        # Arrange
        employee_id = 1
        date_from = None  # Sin fecha de inicio
        date_to = date(2024, 1, 22)
        id = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = sample_timesheet_lines
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, False, id
        )

        # Assert - No debe lanzar excepción

        mock_gateway.all.assert_called_once_with(
            employee_id, None, date_to, None, None, False, None
        )
        assert result == sample_timesheet_lines

    def test_execute_with_date_to_none_and_date_from_valid(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica que date_to=None con date_from válido es permitido."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = None  # Sin fecha de fin
        id = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = sample_timesheet_lines
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, False, id
        )

        # Assert - No debe lanzar excepción

        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, None, None, None, False, None
        )
        assert result == sample_timesheet_lines

    def test_execute_with_all_parameters_none(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica el comportamiento cuando todos los parámetros son None (vista admin completa)."""
        # Arrange - Todos los filtros en None
        id = 1
        user_id = 123

        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = sample_timesheet_lines
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(None, None, None, None, None, False, id)

        # Assert
        mock_employee_gateway.exists_by_id.assert_not_called()  # No valida employee_id cuando es None

        mock_employee_gateway.all.assert_called_once()
        mock_gateway.all.assert_called_once_with(
            None, None, None, None, None, False, None
        )
        assert result == sample_timesheet_lines

    def test_execute_with_negative_project_id(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica el comportamiento con project_id negativo."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        project_id = -1  # Proyecto negativo
        id = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = []  # Gateway maneja el filtro
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, project_id, None, False, id
        )

        # Assert - Debe pasar la validación al gateway (no es responsabilidad del use case validar project_id)

        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, project_id, None, False, None
        )
        assert result == []

    def test_execute_with_empty_employees_dict_but_notification_exists(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_notification,
    ):
        """Test que verifica KeyError cuando employees_dict está vacío pero hay notificaciones."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        id = 1

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.all.return_value = []  # Lista vacía de empleados
        mock_gateway.all.return_value = [sample_timesheet_lines[0]]
        mock_notification_repository.get_by_timesheet_id.return_value = (
            sample_notification
        )

        # Act & Assert - Debe fallar cuando trata de acceder a employees_dict[notification.approver_id]
        with pytest.raises(KeyError):
            use_case.execute(employee_id, date_from, date_to, None, None, False, id)

    def test_execute_with_future_dates(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica el comportamiento con fechas futuras."""
        # Arrange
        employee_id = 1
        date_from = date(2025, 1, 1)  # Fecha futura
        date_to = date(2025, 12, 31)
        id = 1
        user_id = 123

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = []  # Sin timesheets en el futuro
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, False, id
        )

        # Assert

        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, None, False, None
        )
        assert result == []

    def test_execute_with_same_date_from_and_date_to(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica el comportamiento cuando date_from y date_to son la misma fecha."""
        # Arrange
        employee_id = 1
        same_date = date(2024, 1, 15)
        date_from = same_date
        date_to = same_date
        id = 1
        user_id = 123

        # Crear timesheet para esa fecha específica
        same_date_timesheet = [
            DetailedTimesheetLine(
                id=1,
                name="Same Date Timesheet",
                employee_id=1,
                project=Project(id=1, name="Test Project"),
                task=None,
                hours=8.0,
                date=same_date,
                validated=False,
            )
        ]

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.get_user_id_by_employee_id.return_value = user_id
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = same_date_timesheet
        mock_notification_repository.get_by_timesheet_id.return_value = None

        # Act
        result = use_case.execute(
            employee_id, date_from, date_to, None, None, False, id
        )

        # Assert - No debe lanzar excepción

        mock_gateway.all.assert_called_once_with(
            employee_id, date_from, date_to, None, None, False, None
        )
        assert result == same_date_timesheet
        assert len(result) == 1
        assert result[0].date == same_date

    def test_execute_gateway_exception_propagation(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_employees,
    ):
        """Test que verifica que las excepciones del gateway se propagan correctamente."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        id = 1

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.all.return_value = sample_employees
        # Simular excepción específica del dominio
        mock_gateway.all.side_effect = TimesheetListError("Database connection failed")

        # Act & Assert
        with pytest.raises(TimesheetListError) as exc_info:
            use_case.execute(employee_id, date_from, date_to, None, None, False, id)

        assert "Database connection failed" in str(exc_info.value)

    def test_execute_notification_repository_exception_propagation(
        self,
        use_case,
        mock_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        sample_timesheet_lines,
        sample_employees,
    ):
        """Test que verifica que las excepciones del notification_repository se propagan correctamente."""
        # Arrange
        employee_id = 1
        date_from = date(2024, 1, 14)
        date_to = date(2024, 1, 22)
        id = 1

        mock_employee_gateway.exists_by_id.return_value = True
        mock_employee_gateway.all.return_value = sample_employees
        mock_gateway.all.return_value = [sample_timesheet_lines[0]]
        # Simular excepción en el repositorio de notificaciones
        mock_notification_repository.get_by_timesheet_id.side_effect = Exception(
            "Notification DB error"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            use_case.execute(employee_id, date_from, date_to, None, None, False, id)

        assert "Notification DB error" in str(exc_info.value)
