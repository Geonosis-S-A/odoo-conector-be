import pytest
from datetime import date
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.dashboard.api.routers import (
    router,
    get_dashboard_data_gateway,
    get_employee_gateway,
    get_task_gateway,
    get_timesheet_gateway,
    get_notification_repository,
)
from app.dashboard.domain.models import (
    DashboardSummary,
    DashboardSummaryByEmployee,
    KPI,
    ProjectTotal,
    TaskTotal,
    EmployeeTotal,
)
from app.shared.security.roles import Roles
from app.shared.security.dependencies import get_current_user


class TestDashboardRouters:
    """Tests unitarios para los endpoints del dashboard."""

    @pytest.fixture
    def app(self):
        """Fixture que proporciona una nueva app para cada test."""
        test_app = FastAPI()
        test_app.include_router(router)
        return test_app

    @pytest.fixture
    def client(self, app):
        """Fixture que proporciona un TestClient."""
        return TestClient(app)

    @pytest.fixture
    def mock_current_user_admin(self):
        """Mock de usuario con permisos de admin."""
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],
        }

    @pytest.fixture
    def mock_current_user_regular(self):
        """Mock de usuario regular sin permisos de admin."""
        return {
            "user_id": 2,
            "user_email": "user@example.com",
            "user_name": "Regular User",
            "roles": [1],  # Rol de empleado regular (no es approver)
        }

    @pytest.fixture
    def mock_dashboard_data(self):
        """Mock de datos de dashboard completos."""
        return DashboardSummary.create(
            users_count=5,
            hours_selected_period=KPI(total=200.0, average_per_user=40.0, unit="hours"),
            entries_selected_period=KPI(
                total=50.0, average_per_user=10.0, unit="entries"
            ),
            daily_average_hours=KPI(total=8.0, average_per_user=8.0, unit="hours/day"),
            by_project=[
                ProjectTotal(project_id=1, project_name="Project A", hours=100.0),
                ProjectTotal(project_id=2, project_name="Project B", hours=100.0),
            ],
            by_task=[
                TaskTotal(task_id=1, task_name="Task 1", hours=50.0, project_id=1),
                TaskTotal(task_id=2, task_name="Task 2", hours=50.0, project_id=1),
            ],
            by_employee=[
                EmployeeTotal(user_id=1, employee_name="Employee 1", hours=80.0),
                EmployeeTotal(user_id=2, employee_name="Employee 2", hours=120.0),
            ],
            hierarchical_summary=None,  # No incluir por ahora
        )

    @pytest.fixture
    def mock_dashboard_data_by_employee(self):
        """Mock de datos de dashboard por empleado."""
        return DashboardSummaryByEmployee.create(
            users_count=1,
            worked_days=22,
            hours_selected_period=KPI(
                total=160.0, average_per_user=160.0, unit="hours"
            ),
            entries_selected_period=KPI(
                total=22.0, average_per_user=22.0, unit="entries"
            ),
            daily_average_hours=KPI(
                total=7.27, average_per_user=7.27, unit="hours/day"
            ),
            by_project=[
                ProjectTotal(project_id=1, project_name="Project A", hours=80.0),
                ProjectTotal(project_id=2, project_name="Project B", hours=80.0),
            ],
            by_task=[
                TaskTotal(task_id=1, task_name="Task 1", hours=40.0, project_id=1),
                TaskTotal(task_id=2, task_name="Task 2", hours=40.0, project_id=1),
            ],
            by_employee=[
                EmployeeTotal(user_id=1, employee_name="Employee 1", hours=160.0),
            ],
            hierarchical_summary=None,  # No incluir por ahora
        )

    @pytest.fixture
    def mock_dashboard_gateway(self):
        """Mock del gateway de dashboard."""
        return Mock()

    @pytest.fixture
    def mock_employee_gateway(self):
        """Mock del gateway de empleados."""
        mock = Mock()
        mock.get_user_id_by_employee_id.return_value = 123  # user_id mock
        return mock

    @pytest.fixture
    def mock_task_gateway(self):
        """Mock del gateway de tareas."""
        return Mock()

    @pytest.fixture
    def mock_timesheet_gateway(self):
        """Mock del gateway de timesheet."""
        return Mock()

    @pytest.fixture
    def mock_use_case(self):
        """Mock del caso de uso."""
        return Mock()

    def test_get_dashboard_summary_success_admin_user(
        self,
        app,
        client,
        mock_current_user_admin,
        mock_dashboard_data,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
        mock_use_case,
    ):
        """Test exitoso del endpoint get_dashboard_summary con usuario admin."""
        # Arrange
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        mock_use_case.execute.return_value = mock_dashboard_data

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_admin
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        with patch(
            "app.dashboard.api.routers.GetDashboardSummaryUseCase",
            return_value=mock_use_case,
        ):
            # Act
            response = client.get(
                "/dashboard/summary",
                params={
                    "date_from": test_date_from.isoformat(),
                    "date_to": test_date_to.isoformat(),
                },
            )

            # Assert
            assert response.status_code == 200

            data = response.json()
            assert "meta" in data
            assert "summary" in data
            assert "totals" in data
            assert data["meta"]["users_count"] == 5
            assert data["summary"]["hours_selected_period"]["total"] == 200.0
            assert data["summary"]["hours_selected_period"]["average_per_user"] == 40.0
            assert len(data["totals"]["by_project"]) == 2
            assert len(data["totals"]["by_task"]) == 2
            assert len(data["totals"]["by_employee"]) == 2

            # Verificar que se llamó al use case con los parámetros correctos
            mock_employee_gateway.get_user_id_by_employee_id.assert_called_once_with(1)
            mock_use_case.execute.assert_called_once_with(
                123, 1, test_date_from, test_date_to
            )

    def test_get_dashboard_summary_forbidden_regular_user(
        self,
        app,
        client,
        mock_current_user_regular,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test que verifica que usuarios regulares no pueden acceder al dashboard general."""
        # Arrange
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_regular
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Act
        response = client.get(
            "/dashboard/summary",
            params={
                "date_from": test_date_from.isoformat(),
                "date_to": test_date_to.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 403
        assert "No tienes permisos para ver el dashboard" in response.json()["detail"]

    def test_get_dashboard_summary_invalid_date_range(
        self,
        app,
        client,
        mock_current_user_admin,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test que verifica error cuando date_from es posterior a date_to."""
        # Arrange
        test_date_from = date(2024, 1, 31)  # Fecha posterior
        test_date_to = date(2024, 1, 1)  # Fecha anterior

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_admin
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Act
        response = client.get(
            "/dashboard/summary",
            params={
                "date_from": test_date_from.isoformat(),
                "date_to": test_date_to.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 400
        assert (
            "La fecha de inicio no puede ser posterior a la fecha de fin"
            in response.json()["detail"]
        )

    def test_get_dashboard_summary_user_not_found(
        self,
        app,
        client,
        mock_current_user_admin,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test que verifica error cuando no se encuentra el usuario."""
        # Arrange
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        mock_employee_gateway.get_user_id_by_employee_id.return_value = (
            None  # Usuario no encontrado
        )

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_admin
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Act
        response = client.get(
            "/dashboard/summary",
            params={
                "date_from": test_date_from.isoformat(),
                "date_to": test_date_to.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 404
        assert "Usuario no encontrado" in response.json()["detail"]

    def test_get_dashboard_summary_by_employee_success_same_user(
        self,
        app,
        client,
        mock_current_user_regular,
        mock_dashboard_data_by_employee,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
        mock_use_case,
    ):
        """Test exitoso del endpoint get_dashboard_summary_by_employee para el mismo usuario."""
        # Arrange
        test_employee_id = 2  # Mismo ID que el usuario autenticado
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        mock_use_case.execute.return_value = mock_dashboard_data_by_employee

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_regular
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        with patch(
            "app.dashboard.api.routers.GetDashboardSummaryByEmployeeUseCase",
            return_value=mock_use_case,
        ):
            # Act
            response = client.get(
                f"/dashboard/summary/{test_employee_id}",
                params={
                    "date_from": test_date_from.isoformat(),
                    "date_to": test_date_to.isoformat(),
                },
            )

            # Assert
            assert response.status_code == 200

            data = response.json()
            assert "meta" in data
            assert "summary" in data
            assert "totals" in data
            assert data["meta"]["users_count"] == 1
            assert data["meta"]["worked_days"] == 22
            assert data["summary"]["hours_selected_period"]["total"] == 160.0
            assert data["summary"]["hours_selected_period"]["average_per_user"] == 160.0

            # Verificar que se llamó al use case con los parámetros correctos
            mock_use_case.execute.assert_called_once_with(
                test_employee_id, test_date_from, test_date_to
            )

    def test_get_dashboard_summary_by_employee_success_admin_different_user(
        self,
        app,
        client,
        mock_current_user_admin,
        mock_dashboard_data_by_employee,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
        mock_use_case,
    ):
        """Test exitoso del endpoint para admin consultando otro empleado."""
        # Arrange
        test_employee_id = 5  # ID diferente al usuario autenticado (admin)
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        mock_use_case.execute.return_value = mock_dashboard_data_by_employee

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_admin
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        with patch(
            "app.dashboard.api.routers.GetDashboardSummaryByEmployeeUseCase",
            return_value=mock_use_case,
        ):
            # Act
            response = client.get(
                f"/dashboard/summary/{test_employee_id}",
                params={
                    "date_from": test_date_from.isoformat(),
                    "date_to": test_date_to.isoformat(),
                },
            )

            # Assert
            assert response.status_code == 200
            mock_use_case.execute.assert_called_once_with(
                test_employee_id, test_date_from, test_date_to
            )

    def test_get_dashboard_summary_by_employee_forbidden_different_user(
        self,
        app,
        client,
        mock_current_user_regular,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test que verifica que usuarios regulares no pueden consultar otros empleados."""
        # Arrange
        test_employee_id = 5  # ID diferente al usuario autenticado
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_regular
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Act
        response = client.get(
            f"/dashboard/summary/{test_employee_id}",
            params={
                "date_from": test_date_from.isoformat(),
                "date_to": test_date_to.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 403
        assert (
            "No tienes permisos para ver esta información" in response.json()["detail"]
        )

    def test_get_dashboard_summary_by_employee_invalid_date_range(
        self,
        app,
        client,
        mock_current_user_regular,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test que verifica error cuando date_from es posterior a date_to en el endpoint por empleado."""
        # Arrange
        test_employee_id = 2  # Mismo ID que el usuario
        test_date_from = date(2024, 1, 31)  # Fecha posterior
        test_date_to = date(2024, 1, 1)  # Fecha anterior

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_regular
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Act
        response = client.get(
            f"/dashboard/summary/{test_employee_id}",
            params={
                "date_from": test_date_from.isoformat(),
                "date_to": test_date_to.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 400
        assert (
            "La fecha de inicio no puede ser posterior a la fecha de fin"
            in response.json()["detail"]
        )

    def test_get_task_detail_success_with_task_id(
        self,
        app,
        client,
        mock_current_user_admin,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test exitoso del endpoint get_task_detail con task_id."""
        # Arrange
        test_task_id = 1
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        # Mock del repositorio de notificaciones
        mock_notification_repository = Mock()
        app.dependency_overrides[get_notification_repository] = (
            lambda: mock_notification_repository
        )

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_admin
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Mock del caso de uso
        mock_task_detail_data = {
            "task_id": test_task_id,
            "project_id": None,
            "timesheet_lines": [
                {
                    "id": 1,
                    "name": "Desarrollo frontend",
                    "employee": {"employee_id": 1, "employee_name": "Juan Pérez"},
                    "hours": 8.0,
                    "date": test_date_from,
                    "create_date": "2024-01-01T10:00:00Z",
                    "validated": False,
                    "notification": None,
                },
                {
                    "id": 2,
                    "name": "Testing",
                    "employee": {"employee_id": 2, "employee_name": "Ana García"},
                    "hours": 4.0,
                    "date": test_date_from,
                    "create_date": "2024-01-01T14:00:00Z",
                    "validated": True,
                    "notification": {
                        "id": 1,
                        "sender_name": "Manager",
                        "sended_at": "2024-01-02T09:00:00Z",
                    },
                },
            ],
        }

        with patch(
            "app.dashboard.api.routers.GetTaskDetailUseCase"
        ) as mock_use_case_class:
            mock_use_case = Mock()
            mock_use_case.execute.return_value = mock_task_detail_data
            mock_use_case_class.return_value = mock_use_case

            # Act
            response = client.get(
                "/dashboard/summary/detail",
                params={
                    "task_id": test_task_id,
                    "date_from": test_date_from.isoformat(),
                    "date_to": test_date_to.isoformat(),
                },
            )

            # Assert
            assert response.status_code == 200

            data = response.json()
            assert "task_id" in data
            assert "project_id" in data
            assert "timesheet_lines" in data
            assert data["task_id"] == test_task_id
            assert data["project_id"] is None
            assert len(data["timesheet_lines"]) == 2

            # Verificar estructura de timesheet_lines
            timesheet_line = data["timesheet_lines"][0]
            assert "id" in timesheet_line
            assert "name" in timesheet_line
            assert "employee" in timesheet_line
            assert "hours" in timesheet_line
            assert "date" in timesheet_line
            assert "validated" in timesheet_line
            assert "notification" in timesheet_line

            # Verificar que se llamó al use case con los parámetros correctos
            mock_use_case.execute.assert_called_once_with(
                test_task_id, None, test_date_from, test_date_to
            )

    def test_get_task_detail_success_with_project_id(
        self,
        app,
        client,
        mock_current_user_admin,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test exitoso del endpoint get_task_detail con project_id."""
        # Arrange
        test_project_id = 2
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        # Mock del repositorio de notificaciones
        mock_notification_repository = Mock()
        app.dependency_overrides[get_notification_repository] = (
            lambda: mock_notification_repository
        )

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_admin
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Mock del caso de uso
        mock_task_detail_data = {
            "task_id": None,
            "project_id": test_project_id,
            "timesheet_lines": [
                {
                    "id": 3,
                    "name": "Trabajo directo proyecto",
                    "employee": {"employee_id": 3, "employee_name": "Carlos López"},
                    "hours": 6.0,
                    "date": test_date_from,
                    "create_date": None,
                    "validated": False,
                    "notification": None,
                }
            ],
        }

        with patch(
            "app.dashboard.api.routers.GetTaskDetailUseCase"
        ) as mock_use_case_class:
            mock_use_case = Mock()
            mock_use_case.execute.return_value = mock_task_detail_data
            mock_use_case_class.return_value = mock_use_case

            # Act
            response = client.get(
                "/dashboard/summary/detail",
                params={
                    "project_id": test_project_id,
                    "date_from": test_date_from.isoformat(),
                    "date_to": test_date_to.isoformat(),
                },
            )

            # Assert
            assert response.status_code == 200

            data = response.json()
            assert data["task_id"] is None
            assert data["project_id"] == test_project_id
            assert len(data["timesheet_lines"]) == 1

            # Verificar que se llamó al use case con los parámetros correctos
            mock_use_case.execute.assert_called_once_with(
                None, test_project_id, test_date_from, test_date_to
            )

    def test_get_task_detail_forbidden_regular_user(
        self,
        app,
        client,
        mock_current_user_regular,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test que verifica que usuarios regulares no pueden acceder al endpoint de detalle."""
        # Arrange
        test_task_id = 1
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        # Mock del repositorio de notificaciones
        mock_notification_repository = Mock()
        app.dependency_overrides[get_notification_repository] = (
            lambda: mock_notification_repository
        )

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_regular
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Act
        response = client.get(
            "/dashboard/summary/detail",
            params={
                "task_id": test_task_id,
                "date_from": test_date_from.isoformat(),
                "date_to": test_date_to.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 403
        assert (
            "No tienes permisos para ver esta información" in response.json()["detail"]
        )

    def test_get_task_detail_missing_both_ids(
        self,
        app,
        client,
        mock_current_user_admin,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test que verifica error cuando no se proporciona task_id ni project_id."""
        # Arrange
        test_date_from = date(2024, 1, 1)
        test_date_to = date(2024, 1, 31)

        # Mock del repositorio de notificaciones
        mock_notification_repository = Mock()
        app.dependency_overrides[get_notification_repository] = (
            lambda: mock_notification_repository
        )

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_admin
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Act
        response = client.get(
            "/dashboard/summary/detail",
            params={
                "date_from": test_date_from.isoformat(),
                "date_to": test_date_to.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 400
        assert "Debe proporcionar task_id o project_id" in response.json()["detail"]

    def test_get_task_detail_invalid_date_range(
        self,
        app,
        client,
        mock_current_user_admin,
        mock_dashboard_gateway,
        mock_employee_gateway,
        mock_task_gateway,
        mock_timesheet_gateway,
    ):
        """Test que verifica error cuando date_from es posterior a date_to."""
        # Arrange
        test_task_id = 1
        test_date_from = date(2024, 1, 31)  # Fecha posterior
        test_date_to = date(2024, 1, 1)  # Fecha anterior

        # Mock del repositorio de notificaciones
        mock_notification_repository = Mock()
        app.dependency_overrides[get_notification_repository] = (
            lambda: mock_notification_repository
        )

        # Configurar overrides de dependencias
        app.dependency_overrides[get_current_user] = lambda: mock_current_user_admin
        app.dependency_overrides[get_dashboard_data_gateway] = (
            lambda: mock_dashboard_gateway
        )
        app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway
        app.dependency_overrides[get_task_gateway] = lambda: mock_task_gateway
        app.dependency_overrides[get_timesheet_gateway] = lambda: mock_timesheet_gateway

        # Act
        response = client.get(
            "/dashboard/summary/detail",
            params={
                "task_id": test_task_id,
                "date_from": test_date_from.isoformat(),
                "date_to": test_date_to.isoformat(),
            },
        )

        # Assert
        assert response.status_code == 400
        assert (
            "La fecha de inicio no puede ser posterior a la fecha de fin"
            in response.json()["detail"]
        )


class TestDashboardDependencies:
    """Tests unitarios para las funciones de dependencias del dashboard."""

    def test_get_employee_gateway_success(self):
        """Test exitoso de creación del gateway de empleados."""
        # Arrange
        mock_odoo_connection = Mock()

        # Act
        with patch(
            "app.dashboard.api.routers.OdooEmployeeGateway"
        ) as mock_gateway_class:
            mock_gateway_instance = Mock()
            mock_gateway_class.return_value = mock_gateway_instance

            result = get_employee_gateway(mock_odoo_connection)

            # Assert
            assert result == mock_gateway_instance
            mock_gateway_class.assert_called_once_with(mock_odoo_connection)

    def test_get_employee_gateway_connection_error(self):
        """Test que verifica manejo de errores en la conexión del gateway de empleados."""
        # Arrange
        mock_odoo_connection = Mock()

        # Act & Assert
        with patch(
            "app.dashboard.api.routers.OdooEmployeeGateway",
            side_effect=Exception("Connection error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_employee_gateway(mock_odoo_connection)

            assert exc_info.value.status_code == 500
            assert "Error al conectar con el gateway de empleados" in str(
                exc_info.value.detail
            )

    def test_get_timesheet_gateway_success(self):
        """Test exitoso de creación del gateway de timesheet."""
        # Arrange
        mock_odoo_connection = Mock()

        # Act
        with patch(
            "app.dashboard.api.routers.OdooTimesheetLineGateway"
        ) as mock_gateway_class:
            mock_gateway_instance = Mock()
            mock_gateway_class.return_value = mock_gateway_instance

            result = get_timesheet_gateway(mock_odoo_connection)

            # Assert
            assert result == mock_gateway_instance
            mock_gateway_class.assert_called_once_with(mock_odoo_connection)

    def test_get_timesheet_gateway_connection_error(self):
        """Test que verifica manejo de errores en la conexión del gateway de timesheet."""
        # Arrange
        mock_odoo_connection = Mock()

        # Act & Assert
        with patch(
            "app.dashboard.api.routers.OdooTimesheetLineGateway",
            side_effect=Exception("Connection error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_timesheet_gateway(mock_odoo_connection)

            assert exc_info.value.status_code == 500
            assert "Error al conectar con el gateway" in str(exc_info.value.detail)

    def test_get_task_gateway_success(self):
        """Test exitoso de creación del gateway de tareas."""
        # Arrange
        mock_odoo_connection = Mock()

        # Act
        with patch("app.dashboard.api.routers.OdooTaskGateway") as mock_gateway_class:
            mock_gateway_instance = Mock()
            mock_gateway_class.return_value = mock_gateway_instance

            result = get_task_gateway(mock_odoo_connection)

            # Assert
            assert result == mock_gateway_instance
            mock_gateway_class.assert_called_once_with(mock_odoo_connection)

    def test_get_task_gateway_connection_error(self):
        """Test que verifica manejo de errores en la conexión del gateway de tareas."""
        # Arrange
        mock_odoo_connection = Mock()

        # Act & Assert
        with patch(
            "app.dashboard.api.routers.OdooTaskGateway",
            side_effect=Exception("Connection error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_task_gateway(mock_odoo_connection)

            assert exc_info.value.status_code == 500
            assert "Error al conectar con el gateway de tareas" in str(
                exc_info.value.detail
            )

    def test_get_dashboard_data_gateway_success(self):
        """Test exitoso de creación del gateway de datos de dashboard."""
        # Arrange
        mock_odoo_connection = Mock()
        mock_employee_gateway = Mock()
        mock_task_gateway = Mock()
        mock_timesheet_gateway = Mock()

        # Act
        with patch(
            "app.dashboard.api.routers.OdooDashboardDataService"
        ) as mock_service_class:
            mock_service_instance = Mock()
            mock_service_class.return_value = mock_service_instance

            result = get_dashboard_data_gateway(
                mock_odoo_connection,
                mock_employee_gateway,
                mock_task_gateway,
                mock_timesheet_gateway,
            )

            # Assert
            assert result == mock_service_instance
            mock_service_class.assert_called_once_with(
                mock_odoo_connection,
                mock_employee_gateway,
                mock_task_gateway,
                mock_timesheet_gateway,
            )

    def test_get_dashboard_data_gateway_connection_error(self):
        """Test que verifica manejo de errores en la conexión del gateway de dashboard."""
        # Arrange
        mock_odoo_connection = Mock()
        mock_employee_gateway = Mock()
        mock_task_gateway = Mock()
        mock_timesheet_gateway = Mock()

        # Act & Assert
        with patch(
            "app.dashboard.api.routers.OdooDashboardDataService",
            side_effect=Exception("Connection error"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_dashboard_data_gateway(
                    mock_odoo_connection,
                    mock_employee_gateway,
                    mock_task_gateway,
                    mock_timesheet_gateway,
                )

            assert exc_info.value.status_code == 500
            assert "Error al conectar con el gateway de dashboard" in str(
                exc_info.value.detail
            )
