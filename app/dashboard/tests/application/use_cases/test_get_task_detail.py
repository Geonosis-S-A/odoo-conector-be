import pytest
from datetime import date
from unittest.mock import Mock
from app.dashboard.application.use_cases.get_task_detail import GetTaskDetailUseCase
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.task.domain.models import TaskInfo


class TestGetTaskDetailUseCase:
    """Tests unitarios para GetTaskDetailUseCase."""

    @pytest.fixture
    def mock_dashboard_gateway(self):
        """Mock del gateway de dashboard."""
        return Mock()

    @pytest.fixture
    def mock_timesheet_gateway(self):
        """Mock del gateway de timesheet."""
        return Mock()

    @pytest.fixture
    def mock_employee_gateway(self):
        """Mock del gateway de empleados."""
        return Mock()

    @pytest.fixture
    def mock_notification_repository(self):
        """Mock del repositorio de notificaciones."""
        return Mock()

    @pytest.fixture
    def use_case(
        self,
        mock_dashboard_gateway,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
    ):
        """Instancia del caso de uso con mocks."""
        return GetTaskDetailUseCase(
            mock_dashboard_gateway,
            mock_timesheet_gateway,
            mock_employee_gateway,
            mock_notification_repository,
        )

    @pytest.fixture
    def mock_timesheet_lines(self):
        """Mock de líneas de timesheet."""
        return [
            DetailedTimesheetLine(
                id=1,
                name="Desarrollo frontend",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Tarea 1", project_id=1, project_name="Proyecto A"
                ),
                hours=8.0,
                date=date(2024, 1, 1),
                validated=False,
                create_date="2024-01-01T10:00:00Z",
            ),
            DetailedTimesheetLine(
                id=2,
                name="Testing",
                employee_id=2,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Tarea 1", project_id=1, project_name="Proyecto A"
                ),
                hours=4.0,
                date=date(2024, 1, 2),
                validated=True,
                create_date="2024-01-02T14:00:00Z",
            ),
        ]

    def test_execute_success_with_task_id(
        self,
        use_case,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        mock_timesheet_lines,
    ):
        """Test exitoso con task_id."""
        # Arrange
        task_id = 1
        project_id = None
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        # Configurar mocks
        mock_timesheet_gateway.get_by_task_or_project.return_value = (
            mock_timesheet_lines
        )

        # Mock de empleados (batch get_by_ids, usado dos veces en execute)
        mock_employee_1 = Mock()
        mock_employee_1.id = 1
        mock_employee_1.full_name = "Juan Pérez"
        mock_employee_2 = Mock()
        mock_employee_2.id = 2
        mock_employee_2.full_name = "Ana García"
        by_id = {1: mock_employee_1, 2: mock_employee_2}

        def get_by_ids(ids):
            return [by_id[i] for i in ids if i in by_id]

        mock_employee_gateway.get_by_ids.side_effect = get_by_ids

        mock_notification_repository.get_by_timesheet_ids.return_value = []

        # Act
        result = use_case.execute(task_id, project_id, date_from, date_to)

        # Assert
        assert result["task_id"] == task_id
        assert result["project_id"] == project_id
        assert len(result["timesheet_lines"]) == 2

        # Verificar estructura de datos
        timesheet_line = result["timesheet_lines"][0]
        assert timesheet_line["id"] == 1
        assert timesheet_line["name"] == "Desarrollo frontend"
        assert timesheet_line["employee"]["employee_id"] == 1
        assert timesheet_line["employee"]["employee_name"] == "Juan Pérez"
        assert timesheet_line["hours"] == 8.0
        assert timesheet_line["date"] == date(2024, 1, 1)
        assert timesheet_line["validated"] is False
        assert timesheet_line["notification"] is None

        # Verificar llamadas a los mocks
        mock_timesheet_gateway.get_by_task_or_project.assert_called_once_with(
            task_id=task_id,
            project_id=project_id,
            date_from=date_from,
            date_to=date_to,
        )
        assert mock_employee_gateway.get_by_ids.call_count == 2
        mock_notification_repository.get_by_timesheet_ids.assert_called_once_with(
            [1, 2]
        )

    def test_execute_success_with_project_id(
        self,
        use_case,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
    ):
        """Test exitoso con project_id."""
        # Arrange
        task_id = None
        project_id = 2
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        # Mock de timesheet lines para proyecto
        project_timesheet_lines = [
            DetailedTimesheetLine(
                id=3,
                name="Trabajo directo proyecto",
                employee_id=3,
                project=Project(id=2, name="Proyecto B"),
                task=None,  # Sin tarea específica
                hours=6.0,
                date=date(2024, 1, 1),
                validated=False,
                create_date=None,
            ),
        ]

        mock_timesheet_gateway.get_by_task_or_project.return_value = (
            project_timesheet_lines
        )

        # Mock de empleado
        mock_employee_3 = Mock()
        mock_employee_3.id = 3
        mock_employee_3.full_name = "Carlos López"

        mock_employee_gateway.get_by_ids.side_effect = (
            lambda ids: [mock_employee_3] if 3 in ids else []
        )

        mock_notification_repository.get_by_timesheet_ids.return_value = []

        # Act
        result = use_case.execute(task_id, project_id, date_from, date_to)

        # Assert
        assert result["task_id"] == task_id
        assert result["project_id"] == project_id
        assert len(result["timesheet_lines"]) == 1

        timesheet_line = result["timesheet_lines"][0]
        assert timesheet_line["id"] == 3
        assert timesheet_line["name"] == "Trabajo directo proyecto"
        assert timesheet_line["employee"]["employee_id"] == 3
        assert timesheet_line["employee"]["employee_name"] == "Carlos López"
        assert timesheet_line["hours"] == 6.0
        assert timesheet_line["create_date"] is None

        # Verificar llamadas
        mock_timesheet_gateway.get_by_task_or_project.assert_called_once_with(
            task_id=task_id,
            project_id=project_id,
            date_from=date_from,
            date_to=date_to,
        )
        mock_notification_repository.get_by_timesheet_ids.assert_called_once_with([3])

    def test_execute_with_notifications(
        self,
        use_case,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        mock_timesheet_lines,
    ):
        """Test que verifica el manejo de notificaciones."""
        # Arrange
        task_id = 1
        project_id = None
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_timesheet_gateway.get_by_task_or_project.return_value = (
            mock_timesheet_lines
        )

        # Mock de empleados
        mock_employee_1 = Mock()
        mock_employee_1.id = 1
        mock_employee_1.full_name = "Juan Pérez"
        mock_employee_2 = Mock()
        mock_employee_2.id = 2
        mock_employee_2.full_name = "Ana García"

        by_id = {1: mock_employee_1, 2: mock_employee_2}

        def get_by_ids(ids):
            return [by_id[i] for i in ids if i in by_id]

        mock_employee_gateway.get_by_ids.side_effect = get_by_ids

        mock_notification = Mock()
        mock_notification.id = 1
        mock_notification.timesheet_line_id = 1
        # approver_id debe estar en employees_dict (solo empleados de las líneas)
        mock_notification.approver_id = 1
        mock_notification.created_at = "2024-01-02T09:00:00Z"

        mock_notification_repository.get_by_timesheet_ids.return_value = [
            mock_notification
        ]

        # Act
        result = use_case.execute(task_id, project_id, date_from, date_to)

        # Assert
        timesheet_lines = result["timesheet_lines"]

        # Primera línea debe tener notificación
        first_line = timesheet_lines[0]
        assert first_line["notification"] is not None
        assert first_line["notification"]["id"] == 1
        assert first_line["notification"]["sender_name"] == "Juan Pérez"
        assert first_line["notification"]["sended_at"] == "2024-01-02T09:00:00Z"

        # Segunda línea no debe tener notificación
        second_line = timesheet_lines[1]
        assert second_line["notification"] is None

        mock_notification_repository.get_by_timesheet_ids.assert_called_once_with(
            [1, 2]
        )

    def test_execute_error_no_task_id_nor_project_id(
        self,
        use_case,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
    ):
        """Test que verifica error cuando no se proporciona task_id ni project_id."""
        # Arrange
        task_id = None
        project_id = None
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(task_id, project_id, date_from, date_to)

        assert "Debe proporcionar task_id o project_id" in str(exc_info.value)

        # Verificar que no se llamó a ningún gateway
        mock_timesheet_gateway.get_by_task_or_project.assert_not_called()

    def test_execute_error_invalid_date_range(
        self,
        use_case,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
    ):
        """Test que verifica error cuando date_from es posterior a date_to."""
        # Arrange
        task_id = 1
        project_id = None
        date_from = date(2024, 1, 31)  # Fecha posterior
        date_to = date(2024, 1, 1)  # Fecha anterior

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            use_case.execute(task_id, project_id, date_from, date_to)

        assert "La fecha de inicio no puede ser posterior a la fecha de fin" in str(
            exc_info.value
        )

        # Verificar que no se llamó a ningún gateway
        mock_timesheet_gateway.get_by_task_or_project.assert_not_called()

    def test_execute_empty_timesheet_lines(
        self,
        use_case,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
    ):
        """Test con líneas de timesheet vacías."""
        # Arrange
        task_id = 1
        project_id = None
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_timesheet_gateway.get_by_task_or_project.return_value = []
        mock_employee_gateway.get_by_ids.return_value = []
        mock_notification_repository.get_by_timesheet_ids.return_value = []

        # Act
        result = use_case.execute(task_id, project_id, date_from, date_to)

        # Assert
        assert result["task_id"] == task_id
        assert result["project_id"] == project_id
        assert len(result["timesheet_lines"]) == 0

        # Verificar que se llamó al gateway con los parámetros correctos
        mock_timesheet_gateway.get_by_task_or_project.assert_called_once_with(
            task_id=task_id,
            project_id=project_id,
            date_from=date_from,
            date_to=date_to,
        )

    def test_execute_employee_not_found(
        self,
        use_case,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        mock_timesheet_lines,
    ):
        """Test que verifica el manejo cuando no se encuentra un empleado."""
        # Arrange
        task_id = 1
        project_id = None
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_timesheet_gateway.get_by_task_or_project.return_value = (
            mock_timesheet_lines
        )

        mock_employee_gateway.get_by_ids.return_value = []
        mock_notification_repository.get_by_timesheet_ids.return_value = []

        # Act
        result = use_case.execute(task_id, project_id, date_from, date_to)

        # Assert
        timesheet_lines = result["timesheet_lines"]

        # Debe usar nombres genéricos cuando no encuentra el empleado
        assert timesheet_lines[0]["employee"]["employee_name"] == "Empleado 1"
        assert timesheet_lines[1]["employee"]["employee_name"] == "Empleado 2"

    def test_execute_notification_error_handling(
        self,
        use_case,
        mock_timesheet_gateway,
        mock_employee_gateway,
        mock_notification_repository,
        mock_timesheet_lines,
    ):
        """Si falla el batch de notificaciones, el caso de uso propaga la excepción."""
        task_id = 1
        project_id = None
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_timesheet_gateway.get_by_task_or_project.return_value = (
            mock_timesheet_lines
        )

        mock_employee_1 = Mock()
        mock_employee_1.id = 1
        mock_employee_1.full_name = "Juan Pérez"
        mock_employee_2 = Mock()
        mock_employee_2.id = 2
        mock_employee_2.full_name = "Ana García"
        by_id = {1: mock_employee_1, 2: mock_employee_2}

        mock_employee_gateway.get_by_ids.side_effect = lambda ids: [
            by_id[i] for i in ids if i in by_id
        ]

        mock_notification_repository.get_by_timesheet_ids.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(Exception, match="Database error"):
            use_case.execute(task_id, project_id, date_from, date_to)

    def test_get_employee_names_method(
        self,
        use_case,
        mock_employee_gateway,
    ):
        """Test del método privado _get_employee_names."""
        employee_ids = [1, 2, 999]

        mock_employee_1 = Mock()
        mock_employee_1.id = 1
        mock_employee_1.full_name = "Juan Pérez"
        mock_employee_2 = Mock()
        mock_employee_2.id = 2
        mock_employee_2.full_name = "Ana García"

        mock_employee_gateway.get_by_ids.return_value = [
            mock_employee_1,
            mock_employee_2,
        ]

        result = use_case._get_employee_names(employee_ids)

        # Assert
        assert result[1] == "Juan Pérez"
        assert result[2] == "Ana García"
        assert (
            result[999] == "Empleado 999"
        )  # Nombre genérico para empleado no encontrado

    def test_transform_to_simple_format_method(
        self,
        use_case,
        mock_notification_repository,
    ):
        """Test del método privado _transform_to_simple_format."""
        # Arrange
        timesheet_line = DetailedTimesheetLine(
            id=1,
            name="Desarrollo",
            employee_id=1,
            project=Project(id=1, name="Proyecto A"),
            task=TaskInfo(
                id=1, name="Tarea 1", project_id=1, project_name="Proyecto A"
            ),
            hours=8.0,
            date=date(2024, 1, 1),
            validated=True,
            create_date="2024-01-01T10:00:00Z",
        )

        employee_names = {1: "Juan Pérez"}

        # Mock de empleados para notificaciones
        mock_employee = Mock()
        mock_employee.full_name = "Manager"
        employees_dict = {10: mock_employee}

        mock_notification = Mock()
        mock_notification.id = 1
        mock_notification.approver_id = 10
        mock_notification.created_at = "2024-01-02T09:00:00Z"
        notifications_map = {1: mock_notification}

        result = use_case._transform_to_simple_format(
            timesheet_line, employee_names, employees_dict, notifications_map
        )

        # Assert
        assert result["id"] == 1
        assert result["name"] == "Desarrollo"
        assert result["employee"]["employee_id"] == 1
        assert result["employee"]["employee_name"] == "Juan Pérez"
        assert result["hours"] == 8.0
        assert result["date"] == date(2024, 1, 1)
        assert result["create_date"] == "2024-01-01T10:00:00Z"
        assert result["validated"] is True
        assert result["notification"]["id"] == 1
        assert result["notification"]["sender_name"] == "Manager"
        assert result["notification"]["sended_at"] == "2024-01-02T09:00:00Z"

    def test_transform_to_simple_format_without_notification(
        self,
        use_case,
        mock_notification_repository,
    ):
        """Test del método _transform_to_simple_format sin notificación."""
        # Arrange
        timesheet_line = DetailedTimesheetLine(
            id=2,
            name="Testing",
            employee_id=2,
            project=Project(id=1, name="Proyecto A"),
            task=None,  # Sin tarea
            hours=4.0,
            date=date(2024, 1, 2),
            validated=False,
            create_date=None,
        )

        employee_names = {2: "Ana García"}
        employees_dict = {}

        result = use_case._transform_to_simple_format(
            timesheet_line, employee_names, employees_dict, {}
        )

        # Assert
        assert result["id"] == 2
        assert result["name"] == "Testing"
        assert result["employee"]["employee_id"] == 2
        assert result["employee"]["employee_name"] == "Ana García"
        assert result["hours"] == 4.0
        assert result["date"] == date(2024, 1, 2)
        assert result["create_date"] is None
        assert result["validated"] is False
        assert result["notification"] is None
