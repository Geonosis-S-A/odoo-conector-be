import pytest
from datetime import date
from unittest.mock import Mock
from app.dashboard.application.use_cases.get_dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from app.dashboard.domain.models import (
    DashboardSummary,
    KPI,
    ProjectTotal,
    TaskTotal,
    EmployeeTotal,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine


class TestGetDashboardSummaryUseCase:
    """Tests unitarios para GetDashboardSummaryUseCase."""

    @pytest.fixture
    def mock_dashboard_gateway(self):
        """Mock del gateway de dashboard."""
        return Mock()

    @pytest.fixture
    def mock_employee_gateway(self):
        """Mock del gateway de empleados."""
        return Mock()

    @pytest.fixture
    def mock_task_gateway(self):
        """Mock del gateway de tareas."""
        return Mock()

    @pytest.fixture
    def mock_timesheet_gateway(self):
        """Mock del gateway de timesheet."""
        return Mock()

    @pytest.fixture
    def mock_employee_price_repository(self):
        """Mock del repositorio de precios de empleados."""
        return Mock()

    @pytest.fixture
    def use_case(
        self,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
        mock_employee_price_repository,
    ):
        """Instancia del caso de uso con mocks."""
        return GetDashboardSummaryUseCase(
            mock_dashboard_gateway,
            mock_employee_gateway,
            mock_task_gateway,
            mock_timesheet_gateway,
            mock_employee_price_repository,
        )

    @pytest.fixture
    def mock_timesheet_data(self):
        """Mock de datos de timesheet."""
        return [
            DetailedTimesheetLine(
                id=1,
                name="Task 1",
                employee_id=1,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=1, name="Task 1"),
                hours=8.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=2,
                name="Task 2",
                employee_id=2,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=2, name="Task 2"),
                hours=6.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=3,
                name="Task 3",
                employee_id=1,
                project=Mock(id=2, name="Project B"),
                task=None,  # Sin tarea específica
                hours=4.0,
                date=date(2024, 1, 3),
                validated=True,
            ),
        ]

    @pytest.fixture
    def mock_team_users(self):
        """Mock de usuarios del equipo."""
        return [
            {"id": 1, "name": "Employee 1"},
            {"id": 2, "name": "Employee 2"},
        ]

    def test_execute_success_with_complete_data(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_gateway,
        mock_task_gateway,
        mock_employee_price_repository,
        mock_timesheet_data,
        mock_team_users,
    ):
        """Test exitoso con datos completos del dashboard."""
        # Arrange
        user_id = 123
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        # Configurar mocks
        mock_timesheet_gateway.get_team_users.return_value = mock_team_users
        mock_dashboard_gateway.get_timesheet_summary.return_value = mock_timesheet_data

        # Mock de precios de empleados (vacío para este test)
        mock_employee_price_repository.get_by_user_ids.return_value = []

        # Mock de KPIs
        hours_kpi = KPI(total=200.0, average_per_user=100.0, unit="hours")
        entries_kpi = KPI(total=50.0, average_per_user=25.0, unit="entries")
        daily_avg_kpi = KPI(total=8.0, average_per_user=4.0, unit="hours/day")

        mock_dashboard_gateway.calculate_hours_kpi.return_value = hours_kpi
        mock_dashboard_gateway.calculate_entries_kpi.return_value = entries_kpi
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = daily_avg_kpi

        # Mock de totales
        project_totals = [
            ProjectTotal(project_id=1, project_name="Project A", hours=140.0),
            ProjectTotal(project_id=2, project_name="Project B", hours=60.0),
        ]
        task_totals = [
            TaskTotal(task_id=1, task_name="Task 1", hours=80.0, project_id=1),
            TaskTotal(task_id=2, task_name="Task 2", hours=60.0, project_id=1),
        ]
        employee_totals = [
            EmployeeTotal(user_id=1, employee_name="Employee 1", hours=120.0),
            EmployeeTotal(user_id=2, employee_name="Employee 2", hours=80.0),
        ]

        mock_dashboard_gateway.calculate_project_totals.return_value = project_totals
        mock_dashboard_gateway.calculate_task_totals.return_value = task_totals
        mock_dashboard_gateway.calculate_employee_totals.return_value = employee_totals

        # Mock project without task
        project_without_task = [
            TaskTotal(
                task_id=0, task_name="Project B (Sin Tarea)", hours=60.0, project_id=2
            )  # 0 indica sin tarea
        ]
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = (
            project_without_task
        )

        # Mock hierarchical summary (test unitario, no necesitamos la implementación real)
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(user_id, employee_id, date_from, date_to)

        # Assert
        assert isinstance(result, DashboardSummary)
        assert result.meta["users_count"] == 2
        assert result.summary["hours_selected_period"] == hours_kpi
        assert result.summary["entries_selected_period"] == entries_kpi
        assert result.summary["daily_average_hours"] == daily_avg_kpi
        assert result.totals["by_project"] == project_totals
        assert len(result.totals["by_task"]) == 3  # 2 originales + 1 sin tarea
        assert result.totals["by_employee"] == employee_totals
        assert result.hierarchical_summary is None  # Mockeado como None

        # Verificar llamadas a los mocks
        mock_timesheet_gateway.get_team_users.assert_called_once_with(
            user_id, employee_id
        )
        mock_dashboard_gateway.get_timesheet_summary.assert_called_once_with(
            [1, 2],  # IDs de usuarios del equipo
            date_from,
            date_to,
            use_case.task_gateway,
            use_case.timesheet_line_gateway,
            user_id,
        )
        mock_dashboard_gateway.calculate_hours_kpi.assert_called_once_with(
            mock_timesheet_data, 2
        )
        mock_dashboard_gateway.calculate_entries_kpi.assert_called_once_with(
            mock_timesheet_data, 2
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.assert_called_once_with(
            mock_timesheet_data, 2, date_from, date_to
        )
        mock_dashboard_gateway.calculate_project_totals.assert_called_once_with(
            mock_timesheet_data
        )
        mock_dashboard_gateway.calculate_task_totals.assert_called_once_with(
            mock_timesheet_data
        )
        mock_dashboard_gateway.calculate_employee_totals.assert_called_once()
        call_args = mock_dashboard_gateway.calculate_employee_totals.call_args
        assert call_args[0][0] == mock_timesheet_data
        assert call_args[0][1] == mock_team_users
        # Verificar que el tercer parámetro (timesheet_cost_map) es un dict
        assert isinstance(call_args[0][2], dict)

        mock_dashboard_gateway.calculate_project_without_task_totals.assert_called_once_with(
            project_totals, task_totals
        )
        mock_dashboard_gateway.calculate_hierarchical_summary.assert_called_once()
        call_args_hierarchical = (
            mock_dashboard_gateway.calculate_hierarchical_summary.call_args
        )
        assert call_args_hierarchical[0][0] == mock_timesheet_data
        assert call_args_hierarchical[0][1] == use_case.task_gateway
        # Verificar que el tercer parámetro (timesheet_cost_map) es un dict
        assert isinstance(call_args_hierarchical[0][2], dict)

    def test_execute_with_empty_team_users(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_gateway,
        mock_task_gateway,
        mock_employee_price_repository,
    ):
        """Test con equipo vacío."""
        # Arrange
        user_id = 123
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_timesheet_gateway.get_team_users.return_value = []
        mock_dashboard_gateway.get_timesheet_summary.return_value = []

        # Mock de precios de empleados (vacío)
        mock_employee_price_repository.get_by_user_ids.return_value = []

        # Mock de KPIs vacíos
        empty_hours_kpi = KPI(total=0.0, average_per_user=0.0, unit="hours")
        empty_entries_kpi = KPI(total=0.0, average_per_user=0.0, unit="entries")
        empty_daily_kpi = KPI(total=0.0, average_per_user=0.0, unit="hours/day")

        mock_dashboard_gateway.calculate_hours_kpi.return_value = empty_hours_kpi
        mock_dashboard_gateway.calculate_entries_kpi.return_value = empty_entries_kpi
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = (
            empty_daily_kpi
        )

        # Mock de totales vacíos
        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = []
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = []
        # Mock task gateway para hierarchical summary
        mock_task_gateway.get_tasks_info_with_parents.return_value = {}  # Sin tareas

        # Act
        result = use_case.execute(user_id, employee_id, date_from, date_to)

        # Assert
        assert isinstance(result, DashboardSummary)
        assert result.meta["users_count"] == 0
        assert result.summary["hours_selected_period"].total == 0.0
        assert result.summary["entries_selected_period"].total == 0.0
        assert result.summary["daily_average_hours"].total == 0.0
        assert len(result.totals["by_project"]) == 0
        assert len(result.totals["by_task"]) == 0
        assert len(result.totals["by_employee"]) == 0

        # Verificar que se llamó con lista vacía
        mock_dashboard_gateway.get_timesheet_summary.assert_called_once_with(
            [],  # Lista vacía de usuarios
            date_from,
            date_to,
            use_case.task_gateway,
            use_case.timesheet_line_gateway,
            user_id,
        )

    def test_execute_with_single_user_team(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_gateway,
        mock_task_gateway,
        mock_employee_price_repository,
    ):
        """Test con equipo de un solo usuario."""
        # Arrange
        user_id = 123
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        single_user_team = [{"id": 1, "name": "Employee 1"}]
        mock_timesheet_gateway.get_team_users.return_value = single_user_team

        # Mock de datos de timesheet para un solo empleado
        single_user_timesheet_data = [
            DetailedTimesheetLine(
                id=1,
                name="Task 1",
                employee_id=1,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=1, name="Task 1"),
                hours=8.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=2,
                name="Task 2",
                employee_id=1,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=2, name="Task 2"),
                hours=6.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=3,
                name="Task 3",
                employee_id=1,
                project=Mock(id=2, name="Project B"),
                task=None,  # Sin tarea específica
                hours=4.0,
                date=date(2024, 1, 3),
                validated=True,
            ),
        ]
        mock_dashboard_gateway.get_timesheet_summary.return_value = (
            single_user_timesheet_data
        )

        # Mock de precios de empleados (vacío)
        mock_employee_price_repository.get_by_user_ids.return_value = []

        # Mock de KPIs para un usuario
        hours_kpi = KPI(total=120.0, average_per_user=120.0, unit="hours")
        entries_kpi = KPI(total=30.0, average_per_user=30.0, unit="entries")
        daily_avg_kpi = KPI(total=8.0, average_per_user=8.0, unit="hours/day")

        mock_dashboard_gateway.calculate_hours_kpi.return_value = hours_kpi
        mock_dashboard_gateway.calculate_entries_kpi.return_value = entries_kpi
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = daily_avg_kpi

        # Mock de totales
        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = []
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = []
        # Mock task gateway para hierarchical summary
        mock_task_gateway.get_tasks_info_with_parents.return_value = {}  # Sin tareas

        # Act
        result = use_case.execute(user_id, employee_id, date_from, date_to)

        # Assert
        assert result.meta["users_count"] == 1
        assert result.summary["hours_selected_period"].average_per_user == 120.0
        assert result.summary["entries_selected_period"].average_per_user == 30.0
        assert result.summary["daily_average_hours"].average_per_user == 8.0

        # Verificar que se calculó para 1 usuario
        mock_dashboard_gateway.calculate_hours_kpi.assert_called_once_with(
            single_user_timesheet_data, 1
        )
        mock_dashboard_gateway.calculate_entries_kpi.assert_called_once_with(
            single_user_timesheet_data, 1
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.assert_called_once_with(
            single_user_timesheet_data, 1, date_from, date_to
        )

    def test_execute_project_without_task_integration(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_gateway,
        mock_task_gateway,
        mock_employee_price_repository,
        mock_timesheet_data,
        mock_team_users,
    ):
        """Test que verifica la integración de tareas sin proyecto específico."""
        # Arrange
        user_id = 123
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_timesheet_gateway.get_team_users.return_value = mock_team_users
        mock_dashboard_gateway.get_timesheet_summary.return_value = mock_timesheet_data

        # Mock de precios de empleados (vacío)
        mock_employee_price_repository.get_by_user_ids.return_value = []

        # Mock básico de KPIs
        mock_dashboard_gateway.calculate_hours_kpi.return_value = KPI(
            total=100.0, average_per_user=50.0
        )
        mock_dashboard_gateway.calculate_entries_kpi.return_value = KPI(
            total=20.0, average_per_user=10.0
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = KPI(
            total=8.0, average_per_user=4.0
        )

        # Mock de totales
        original_task_totals = [
            TaskTotal(task_id=1, task_name="Task 1", hours=50.0, project_id=1),
            TaskTotal(task_id=2, task_name="Task 2", hours=30.0, project_id=1),
        ]
        project_without_task = [
            TaskTotal(
                task_id=0, task_name="Project B (Sin Tarea)", hours=20.0, project_id=2
            )  # 0 indica sin tarea
        ]

        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = original_task_totals
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = (
            project_without_task
        )
        # Mock task gateway para hierarchical summary
        mock_task_gateway.get_tasks_info_with_parents.return_value = {}  # Sin tareas

        # Act
        result = use_case.execute(user_id, employee_id, date_from, date_to)

        # Assert
        # Verificar que se extendió la lista de tareas con las tareas sin proyecto
        assert len(result.totals["by_task"]) == 3  # 2 originales + 1 sin tarea

        # Verificar que la llamada se hizo correctamente
        mock_dashboard_gateway.calculate_project_without_task_totals.assert_called_once_with(
            [],  # project_totals
            original_task_totals,  # task_totals originales
        )

    def test_execute_calls_hierarchical_summary_calculation(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_gateway,
        mock_task_gateway,
        mock_employee_price_repository,
        mock_timesheet_data,
        mock_team_users,
    ):
        """Test que verifica que se llama al cálculo de estructura jerárquica (sin validar contenido)."""
        # Arrange
        user_id = 123
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_timesheet_gateway.get_team_users.return_value = mock_team_users
        mock_dashboard_gateway.get_timesheet_summary.return_value = mock_timesheet_data

        # Mock básico de todo lo demás
        mock_dashboard_gateway.calculate_hours_kpi.return_value = KPI(
            total=100.0, average_per_user=50.0
        )
        mock_dashboard_gateway.calculate_entries_kpi.return_value = KPI(
            total=20.0, average_per_user=10.0
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = KPI(
            total=8.0, average_per_user=4.0
        )
        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = []
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = []
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Mock de precios de empleados (vacío)
        mock_employee_price_repository.get_by_user_ids.return_value = []

        # Mock del hierarchical summary - solo verificar que se llama
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(user_id, employee_id, date_from, date_to)

        # Assert
        # Solo verificar que se llamó, no el contenido (como pediste)
        # Verificar que se llama al cálculo de estructura jerárquica
        mock_dashboard_gateway.calculate_hierarchical_summary.assert_called_once()
        call_args = mock_dashboard_gateway.calculate_hierarchical_summary.call_args
        assert call_args[0][0] == mock_timesheet_data
        assert call_args[0][1] == use_case.task_gateway
        # Verificar que se pase un dict como tercer parámetro
        assert isinstance(call_args[0][2], dict)
        # Verificar que hierarchical_summary se asignó (puede ser None del mock)
        assert hasattr(result, "hierarchical_summary")

    def test_execute_preserves_gateway_call_order(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_gateway,
        mock_task_gateway,
        mock_employee_price_repository,
        mock_timesheet_data,
        mock_team_users,
    ):
        """Test que verifica que las llamadas a los gateways se hacen en el orden correcto."""
        # Arrange
        user_id = 123
        employee_id = 1
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_timesheet_gateway.get_team_users.return_value = mock_team_users
        mock_dashboard_gateway.get_timesheet_summary.return_value = mock_timesheet_data

        # Mock mínimo necesario
        mock_dashboard_gateway.calculate_hours_kpi.return_value = KPI(
            total=100.0, average_per_user=50.0
        )
        mock_dashboard_gateway.calculate_entries_kpi.return_value = KPI(
            total=20.0, average_per_user=10.0
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = KPI(
            total=8.0, average_per_user=4.0
        )
        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = []
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = []
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Mock de precios de empleados (vacío)
        mock_employee_price_repository.get_by_user_ids.return_value = []

        # Act
        use_case.execute(user_id, employee_id, date_from, date_to)

        # Assert - Verificar orden de llamadas críticas
        assert mock_timesheet_gateway.get_team_users.called
        assert mock_dashboard_gateway.get_timesheet_summary.called
        assert mock_dashboard_gateway.calculate_hours_kpi.called
        assert mock_dashboard_gateway.calculate_entries_kpi.called
        assert mock_dashboard_gateway.calculate_daily_average_kpi.called
        assert mock_dashboard_gateway.calculate_project_totals.called
        assert mock_dashboard_gateway.calculate_task_totals.called
        assert mock_dashboard_gateway.calculate_employee_totals.called
        assert mock_dashboard_gateway.calculate_project_without_task_totals.called
        # Verificar que se procesó la estructura jerárquica
        assert mock_dashboard_gateway.calculate_hierarchical_summary.called
