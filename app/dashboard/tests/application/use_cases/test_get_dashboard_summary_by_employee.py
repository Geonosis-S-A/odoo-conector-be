import pytest
from datetime import date
from unittest.mock import Mock
from app.dashboard.application.use_cases.get_dashboard_summary_by_employee import (
    GetDashboardSummaryByEmployeeUseCase,
)
from app.dashboard.domain.models import (
    DashboardSummaryByEmployee,
    KPI,
    ProjectTotal,
    TaskTotal,
    EmployeeTotal,
)
from app.timesheet_line.domain.models import DetailedTimesheetLine


class TestGetDashboardSummaryByEmployeeUseCase:
    """Tests unitarios para GetDashboardSummaryByEmployeeUseCase."""

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
    def use_case(
        self,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Instancia del caso de uso con mocks."""
        return GetDashboardSummaryByEmployeeUseCase(
            mock_dashboard_gateway,
            mock_employee_gateway,
            mock_task_gateway,
            mock_timesheet_gateway,
        )

    @pytest.fixture
    def mock_timesheet_data_single_employee(self):
        """Mock de datos de timesheet para un solo empleado."""
        return [
            DetailedTimesheetLine(
                id=1,
                name="Task 1",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=1, name="Task 1"),
                hours=8.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=2,
                name="Task 2",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=2, name="Task 2"),
                hours=6.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=3,
                name="Project B work",
                employee_id=5,
                project=Mock(id=2, name="Project B"),
                task=None,  # Sin tarea específica
                hours=4.0,
                date=date(2024, 1, 3),
                validated=True,
            ),
            DetailedTimesheetLine(
                id=4,
                name="Task 1 continued",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=1, name="Task 1"),
                hours=8.0,
                date=date(2024, 1, 4),
                validated=False,
            ),
        ]

    def test_execute_success_with_complete_data(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_data_single_employee,
    ):
        """Test exitoso con datos completos para un empleado."""
        # Arrange
        employee_id = 5
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        # Configurar mock de timesheet data
        mock_dashboard_gateway.get_timesheet_summary.return_value = (
            mock_timesheet_data_single_employee
        )

        # Mock de KPIs
        hours_kpi = KPI(total=160.0, average_per_user=160.0, unit="hours")
        entries_kpi = KPI(total=20.0, average_per_user=20.0, unit="entries")
        daily_avg_kpi = KPI(total=7.27, average_per_user=7.27, unit="hours/day")

        mock_dashboard_gateway.calculate_hours_kpi.return_value = hours_kpi
        mock_dashboard_gateway.calculate_entries_kpi.return_value = entries_kpi
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = daily_avg_kpi

        # Mock de totales
        project_totals = [
            ProjectTotal(project_id=1, project_name="Project A", hours=120.0),
            ProjectTotal(project_id=2, project_name="Project B", hours=40.0),
        ]
        task_totals = [
            TaskTotal(task_id=1, task_name="Task 1", hours=100.0, project_id=1),
            TaskTotal(task_id=2, task_name="Task 2", hours=20.0, project_id=1),
        ]
        employee_totals = [
            EmployeeTotal(user_id=5, employee_name="Employee 5", hours=160.0),
        ]

        mock_dashboard_gateway.calculate_project_totals.return_value = project_totals
        mock_dashboard_gateway.calculate_task_totals.return_value = task_totals
        mock_dashboard_gateway.calculate_employee_totals.return_value = employee_totals

        # Mock project without task
        project_without_task = [
            TaskTotal(
                task_id=0, task_name="Project B (Sin Tarea)", hours=40.0, project_id=2
            )  # 0 indica sin tarea
        ]
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = (
            project_without_task
        )

        # Mock hierarchical summary (no vamos a testear por ahora)
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        assert isinstance(result, DashboardSummaryByEmployee)
        assert result.meta["users_count"] == 1
        assert result.worked_days == 4  # 4 días diferentes trabajados
        assert result.summary["hours_selected_period"] == hours_kpi
        assert result.summary["entries_selected_period"] == entries_kpi
        assert result.summary["daily_average_hours"] == daily_avg_kpi
        assert result.totals["by_project"] == project_totals
        assert len(result.totals["by_task"]) == 3  # 2 originales + 1 sin tarea
        assert result.totals["by_employee"] == employee_totals
        assert result.hierarchical_summary is None

        # Verificar llamadas a los mocks
        mock_dashboard_gateway.get_timesheet_summary.assert_called_once_with(
            [employee_id],  # Lista con un solo empleado
            date_from,
            date_to,
            use_case.task_gateway,
            use_case.timesheet_line_gateway,
        )
        mock_dashboard_gateway.calculate_hours_kpi.assert_called_once_with(
            mock_timesheet_data_single_employee, 1
        )
        mock_dashboard_gateway.calculate_entries_kpi.assert_called_once_with(
            mock_timesheet_data_single_employee, 1
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.assert_called_once_with(
            mock_timesheet_data_single_employee, 1, date_from, date_to
        )
        mock_dashboard_gateway.calculate_employee_totals.assert_called_once_with(
            mock_timesheet_data_single_employee, [{"id": employee_id}]
        )

    def test_execute_calculates_worked_days_correctly(
        self,
        use_case,
        mock_dashboard_gateway,
    ):
        """Test que verifica el cálculo correcto de días trabajados."""
        # Arrange
        employee_id = 5
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        # Datos con días repetidos y horas cero
        timesheet_data_with_repeated_days = [
            DetailedTimesheetLine(
                id=1,
                name="Task 1",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=1, name="Task 1"),
                hours=8.0,
                date=date(2024, 1, 1),  # Día 1
                validated=False,
            ),
            DetailedTimesheetLine(
                id=2,
                name="Task 2",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=2, name="Task 2"),
                hours=4.0,
                date=date(2024, 1, 1),  # Día 1 repetido
                validated=False,
            ),
            DetailedTimesheetLine(
                id=3,
                name="No work",
                employee_id=5,
                project=Mock(id=2, name="Project B"),
                task=None,
                hours=0.0,  # Horas cero - no debe contar
                date=date(2024, 1, 2),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=4,
                name="Task 3",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=3, name="Task 3"),
                hours=6.0,
                date=date(2024, 1, 3),  # Día 3
                validated=False,
            ),
        ]

        mock_dashboard_gateway.get_timesheet_summary.return_value = (
            timesheet_data_with_repeated_days
        )

        # Mock básico de otros cálculos
        mock_dashboard_gateway.calculate_hours_kpi.return_value = KPI(
            total=100.0, average_per_user=100.0
        )
        mock_dashboard_gateway.calculate_entries_kpi.return_value = KPI(
            total=20.0, average_per_user=20.0
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = KPI(
            total=8.0, average_per_user=8.0
        )
        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = []
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = []
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        # Solo debe contar días 1 y 3 (día 2 tiene horas=0, no cuenta)
        assert result.worked_days == 2

    def test_execute_with_no_timesheet_data(
        self,
        use_case,
        mock_dashboard_gateway,
    ):
        """Test con empleado sin datos de timesheet."""
        # Arrange
        employee_id = 5
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_dashboard_gateway.get_timesheet_summary.return_value = []

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
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        assert isinstance(result, DashboardSummaryByEmployee)
        assert result.meta["users_count"] == 1
        assert result.worked_days == 0  # Sin días trabajados
        assert result.summary["hours_selected_period"].total == 0.0
        assert result.summary["entries_selected_period"].total == 0.0
        assert result.summary["daily_average_hours"].total == 0.0
        assert len(result.totals["by_project"]) == 0
        assert len(result.totals["by_task"]) == 0
        assert len(result.totals["by_employee"]) == 0

    def test_execute_project_without_task_integration(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_data_single_employee,
    ):
        """Test que verifica la integración de tareas sin proyecto específico."""
        # Arrange
        employee_id = 5
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_dashboard_gateway.get_timesheet_summary.return_value = (
            mock_timesheet_data_single_employee
        )

        # Mock básico de KPIs
        mock_dashboard_gateway.calculate_hours_kpi.return_value = KPI(
            total=100.0, average_per_user=100.0
        )
        mock_dashboard_gateway.calculate_entries_kpi.return_value = KPI(
            total=20.0, average_per_user=20.0
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = KPI(
            total=8.0, average_per_user=8.0
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
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        # Verificar que se extendió la lista de tareas con las tareas sin proyecto
        assert len(result.totals["by_task"]) == 3  # 2 originales + 1 sin tarea

        # Verificar que la llamada se hizo correctamente
        mock_dashboard_gateway.calculate_project_without_task_totals.assert_called_once_with(
            [],  # project_totals
            original_task_totals,  # task_totals originales
        )

    def test_execute_single_employee_calculation(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_data_single_employee,
    ):
        """Test que verifica que siempre se calcula para 1 usuario (empleado individual)."""
        # Arrange
        employee_id = 5
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_dashboard_gateway.get_timesheet_summary.return_value = (
            mock_timesheet_data_single_employee
        )

        # Mock de KPIs
        mock_dashboard_gateway.calculate_hours_kpi.return_value = KPI(
            total=160.0, average_per_user=160.0
        )
        mock_dashboard_gateway.calculate_entries_kpi.return_value = KPI(
            total=20.0, average_per_user=20.0
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = KPI(
            total=8.0, average_per_user=8.0
        )

        # Mock básico de totales
        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = []
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = []
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        assert result.meta["users_count"] == 1

        # Verificar que todos los cálculos de KPI se hicieron para 1 usuario
        mock_dashboard_gateway.calculate_hours_kpi.assert_called_once_with(
            mock_timesheet_data_single_employee, 1
        )
        mock_dashboard_gateway.calculate_entries_kpi.assert_called_once_with(
            mock_timesheet_data_single_employee, 1
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.assert_called_once_with(
            mock_timesheet_data_single_employee, 1, date_from, date_to
        )

        # Verificar que el cálculo de empleados se hizo con el ID correcto
        mock_dashboard_gateway.calculate_employee_totals.assert_called_once_with(
            mock_timesheet_data_single_employee, [{"id": employee_id}]
        )

    def test_execute_calls_hierarchical_summary_calculation(
        self,
        use_case,
        mock_dashboard_gateway,
        mock_timesheet_data_single_employee,
    ):
        """Test que verifica que se llama al cálculo de estructura jerárquica (sin validar contenido)."""
        # Arrange
        employee_id = 5
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        mock_dashboard_gateway.get_timesheet_summary.return_value = (
            mock_timesheet_data_single_employee
        )

        # Mock básico de todo lo demás
        mock_dashboard_gateway.calculate_hours_kpi.return_value = KPI(
            total=100.0, average_per_user=100.0
        )
        mock_dashboard_gateway.calculate_entries_kpi.return_value = KPI(
            total=20.0, average_per_user=20.0
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = KPI(
            total=8.0, average_per_user=8.0
        )
        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = []
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = []

        # Mock del hierarchical summary - solo verificar que se llama
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        # Solo verificar que se llamó, no el contenido (como pediste)
        mock_dashboard_gateway.calculate_hierarchical_summary.assert_called_once_with(
            mock_timesheet_data_single_employee, use_case.task_gateway
        )
        assert result.hierarchical_summary is None  # Por ahora None

    def test_execute_worked_days_calculation_edge_cases(
        self,
        use_case,
        mock_dashboard_gateway,
    ):
        """Test casos edge para el cálculo de días trabajados."""
        # Arrange
        employee_id = 5
        date_from = date(2024, 1, 1)
        date_to = date(2024, 1, 31)

        # Datos con casos edge: misma fecha múltiples veces, horas negativas, etc.
        edge_case_data = [
            DetailedTimesheetLine(
                id=1,
                name="Task 1",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=1, name="Task 1"),
                hours=8.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=2,
                name="Task 1 continued",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=1, name="Task 1"),
                hours=2.0,
                date=date(2024, 1, 1),  # Mismo día
                validated=False,
            ),
            DetailedTimesheetLine(
                id=3,
                name="Correction",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=1, name="Task 1"),
                hours=-1.0,  # Horas negativas (corrección)
                date=date(2024, 1, 2),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=4,
                name="Zero hours",
                employee_id=5,
                project=Mock(id=2, name="Project B"),
                task=None,
                hours=0.0,  # Horas cero
                date=date(2024, 1, 3),
                validated=False,
            ),
            DetailedTimesheetLine(
                id=5,
                name="Small work",
                employee_id=5,
                project=Mock(id=1, name="Project A"),
                task=Mock(id=2, name="Task 2"),
                hours=0.5,  # Horas pequeñas pero > 0
                date=date(2024, 1, 4),
                validated=False,
            ),
        ]

        mock_dashboard_gateway.get_timesheet_summary.return_value = edge_case_data

        # Mock básico de otros cálculos
        mock_dashboard_gateway.calculate_hours_kpi.return_value = KPI(
            total=100.0, average_per_user=100.0
        )
        mock_dashboard_gateway.calculate_entries_kpi.return_value = KPI(
            total=20.0, average_per_user=20.0
        )
        mock_dashboard_gateway.calculate_daily_average_kpi.return_value = KPI(
            total=8.0, average_per_user=8.0
        )
        mock_dashboard_gateway.calculate_project_totals.return_value = []
        mock_dashboard_gateway.calculate_task_totals.return_value = []
        mock_dashboard_gateway.calculate_employee_totals.return_value = []
        mock_dashboard_gateway.calculate_project_without_task_totals.return_value = []
        mock_dashboard_gateway.calculate_hierarchical_summary.return_value = None

        # Act
        result = use_case.execute(employee_id, date_from, date_to)

        # Assert
        # Días trabajados: 1 (8.0 + 2.0 > 0), 4 (0.5 > 0)
        # Día 2 NO cuenta porque -1.0 no es > 0
        # Día 3 NO cuenta porque 0.0 no es > 0
        assert result.worked_days == 2
