import pytest
from typing import Optional, List
from datetime import datetime
from fastapi.testclient import TestClient
from app.timesheet_line.tests.utils.date_utils import get_valid_test_date, get_multiple_test_dates
from app.email.api.dependencies import get_common_email_service
from app.timesheet_line.api.routers import (
    get_notification_repository,
    get_employee_gateway,
)
from app.timesheet_line.domain.repositories import TimesheetLineNotificationRepository
from app.timesheet_line.domain.models import (
    CreateTimesheetLineNotification,
    DetailedTimesheetLine,
)
from app.users.domain.models import Employee
from app.users.domain.repositories import EmployeeGateway
from sqlmodel import Session


class MockEmailService:
    """Servicio de email que simula el envío pero no hace nada real."""

    def __init__(self):
        self.send_review_mail_calls = []
        self.send_support_mail_calls = []

    async def send_support_mail(
        self, user_name: str, subject: str, body: str, date: datetime
    ) -> None:
        """Simula el envío de un email de soporte."""
        self.send_support_mail_calls.append(
            {"user_name": user_name, "subject": subject, "body": body, "date": date}
        )
        # No hace nada real, solo registra la llamada
        pass

    async def send_review_mail(
        self,
        user_mail: str,
        approver_mail: str,
        timesheet_lines: List[DetailedTimesheetLine],
        body: Optional[str] = None,
    ) -> None:
        """Simula el envío de un email de revisión."""
        self.send_review_mail_calls.append(
            {
                "user_mail": user_mail,
                "approver_mail": approver_mail,
                "timesheet_lines": timesheet_lines,
                "body": body,
            }
        )
        # No hace nada real, solo registra la llamada
        pass

    def reset_calls(self):
        """Resetea el registro de llamadas."""
        self.send_review_mail_calls = []
        self.send_support_mail_calls = []


class MockNotificationRepository:
    """Repositorio de notificaciones que simula la creación pero no hace nada real."""

    def __init__(self):
        self.create_calls = []

    def create(
        self, timesheet_line_notification: CreateTimesheetLineNotification
    ) -> bool:
        """Simula la creación de una notificación."""
        self.create_calls.append(timesheet_line_notification)
        return True

    def delete(self, timesheet_line_notification_id: int) -> bool:
        """Simula la eliminación de una notificación."""
        return True

    def get_by_timesheet_id(self, timesheet_line_id: int) -> None:
        """Simula la consulta de notificación por timesheet ID."""
        return None

    def get_by_timesheet_ids(self, timesheet_line_ids: List[int]) -> List:
        """Simula la consulta de notificaciones por timesheet IDs."""
        return []

    def reset_calls(self):
        """Resetea el registro de llamadas."""
        self.create_calls = []


class MockEmployeeGateway:
    """Gateway de empleados que simula las consultas pero no hace nada real."""

    def __init__(self):
        # Empleados de prueba predefinidos
        self.employees = [
            Employee(id=1, full_name="Test Employee", email="test@example.com"),
            Employee(id=2, full_name="Admin User", email="admin@example.com"),
        ]

    def get_by_email(self, email: str) -> Employee | None:
        """Simula la búsqueda de empleado por email."""
        for employee in self.employees:
            if employee.email == email:
                return employee
        return None

    def get_by_id(self, employee_id: int) -> Employee | None:
        """Simula la búsqueda de empleado por ID."""
        for employee in self.employees:
            if employee.id == employee_id:
                return employee
        return None

    def exists_by_id(self, employee_id: int) -> bool:
        """Simula la verificación de existencia de empleado por ID."""
        return any(emp.id == employee_id for emp in self.employees)

    def all(self) -> List[Employee]:
        """Simula la obtención de todos los empleados."""
        return self.employees


@pytest.fixture
def mock_email_service():
    """Servicio de email simulado para evitar enviar correos reales."""
    service = MockEmailService()
    service.reset_calls()
    return service


@pytest.fixture
def mock_notification_repository():
    """Repositorio de notificaciones simulado."""
    repo = MockNotificationRepository()
    repo.reset_calls()
    return repo


@pytest.fixture
def mock_employee_gateway():
    """Gateway de empleados simulado."""
    return MockEmployeeGateway()


@pytest.mark.integration
def test_send_review_mail_success_admin_user(
    test_client, mock_email_service, mock_notification_repository, mock_employee_gateway
):
    """Test de integración que prueba el envío exitoso de correos de revisión con usuario admin."""
    # Mock admin user
    from app.main import app
    from app.shared.security.dependencies import get_current_user

    async def mock_admin_user():
        #levantar el rol approver del dev.py
        from app.shared.security.role_enums.dev import Roles
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Admin role
        }

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_common_email_service] = lambda: mock_email_service
    app.dependency_overrides[get_notification_repository] = (
        lambda: mock_notification_repository
    )
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    try:
        # Arrange - Crear líneas de timesheet primero
        test_date = get_valid_test_date()
        create_data = [
            {
                "name": "Test Timesheet for Review",
                "employee_id": 1,
                "project_id": 1,
                "hours": 8.0,
                "date": test_date,
            }
        ]
        create_response = test_client.post("/api/v1/timesheet/", json=create_data)
        assert create_response.status_code == 200
        created_id = create_response.json()[0]["id"]

        # Prepare review request
        review_request = {
            "approver_mail": "admin@example.com",
            "body": "Por favor revisa estos registros de horas",
            "timesheetline_ids": [created_id],
        }

        # Act - Enviar correo de revisión
        response = test_client.post("/api/v1/timesheet/review", json=review_request)

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Emails enviados correctamente!"

        # Verificar que se llamó al servicio de email
        assert len(mock_email_service.send_review_mail_calls) == 1
        email_call = mock_email_service.send_review_mail_calls[0]

        # Verificar argumentos del email
        assert email_call["approver_mail"] == "admin@example.com"
        assert email_call["body"] == "Por favor revisa estos registros de horas"
        assert len(email_call["timesheet_lines"]) == 1

        # Verificar que se creó la notificación
        assert len(mock_notification_repository.create_calls) == 1
        notification_call = mock_notification_repository.create_calls[0]
        assert isinstance(notification_call, CreateTimesheetLineNotification)
        assert notification_call.timesheet_line_id == created_id

        # Cleanup
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
        )
        assert delete_response.status_code == 200

    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_send_review_mail_permission_denied_non_admin_user(
    test_client, mock_email_service, mock_employee_gateway
):
    """Test de integración que verifica que un usuario no admin no puede enviar correos de revisión."""
    # Override dependencies (normal user by default has role [1])
    from app.main import app

    app.dependency_overrides[get_common_email_service] = lambda: mock_email_service
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    try:
        # Arrange
        review_request = {
            "approver_mail": "admin@example.com",
            "body": "Por favor revisa estos registros de horas",
            "timesheetline_ids": [1],
        }

        # Act
        response = test_client.post("/api/v1/timesheet/review", json=review_request)

        # Assert
        assert response.status_code == 403
        assert (
            "No tienes permisos para enviar correos de revisión"
            in response.json()["detail"]
        )

        # Verificar que NO se llamó al servicio de email
        assert len(mock_email_service.send_review_mail_calls) == 0

    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_send_review_mail_approver_not_found(
    test_client, mock_email_service, mock_employee_gateway
):
    """Test de integración que verifica el error cuando el empleado aprobador no existe."""
    # Mock admin user
    from app.main import app
    from app.shared.security.dependencies import get_current_user
    from app.shared.security.role_enums.dev import Roles
    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Admin role
        }

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_common_email_service] = lambda: mock_email_service
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    try:
        # Arrange
        review_request = {
            "approver_mail": "nonexistent@example.com",  # Email que no existe
            "body": "Por favor revisa estos registros de horas",
            "timesheetline_ids": [1],
        }

        # Act
        response = test_client.post("/api/v1/timesheet/review", json=review_request)

        # Assert
        assert response.status_code == 404
        assert (
            "El empleado que intenta enviar el correo de revisión no existe"
            in response.json()["detail"]
        )

        # Verificar que NO se llamó al servicio de email
        assert len(mock_email_service.send_review_mail_calls) == 0

    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_send_review_mail_multiple_timesheets_same_employee(
    test_client, mock_email_service, mock_notification_repository, mock_employee_gateway
):
    """Test de integración que prueba el envío de correos para múltiples timesheets del mismo empleado."""
    # Mock admin user
    from app.main import app
    from app.shared.security.dependencies import get_current_user
    from app.shared.security.role_enums.dev import Roles
    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Admin role
        }

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_common_email_service] = lambda: mock_email_service
    app.dependency_overrides[get_notification_repository] = (
        lambda: mock_notification_repository
    )
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    try:
        # Arrange - Crear múltiples líneas de timesheet para el mismo empleado
        test_dates = get_multiple_test_dates(2)
        create_data = [
            {
                "name": "Test Timesheet 1 for Review",
                "employee_id": 1,
                "project_id": 1,
                "hours": 4.0,
                "date": test_dates[0],
            },
            {
                "name": "Test Timesheet 2 for Review",
                "employee_id": 1,
                "project_id": 1,
                "hours": 4.0,
                "date": test_dates[1],
            },
        ]
        create_response = test_client.post("/api/v1/timesheet/", json=create_data)
        assert create_response.status_code == 200
        created_ids = [item["id"] for item in create_response.json()]
        assert len(created_ids) == 2

        # Prepare review request
        review_request = {
            "approver_mail": "admin@example.com",
            "body": "Por favor revisa estos múltiples registros de horas",
            "timesheetline_ids": created_ids,
        }

        # Act
        response = test_client.post("/api/v1/timesheet/review", json=review_request)

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Emails enviados correctamente!"

        # Verificar que se llamó al servicio de email una vez (un email por empleado)
        assert len(mock_email_service.send_review_mail_calls) == 1
        email_call = mock_email_service.send_review_mail_calls[0]

        # Verificar que se enviaron ambos timesheets en un solo email
        assert len(email_call["timesheet_lines"]) == 2

        # Verificar que se crearon las notificaciones para cada timesheet
        assert len(mock_notification_repository.create_calls) == 2

        # Cleanup
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": created_ids}
        )
        assert delete_response.status_code == 200

    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_send_review_mail_without_body(
    test_client, mock_email_service, mock_notification_repository, mock_employee_gateway
):
    """Test de integración que prueba el envío de correos sin mensaje en el body (body opcional)."""
    # Mock admin user
    from app.main import app
    from app.shared.security.dependencies import get_current_user
    from app.shared.security.role_enums.dev import Roles
    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Admin role
        }

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_common_email_service] = lambda: mock_email_service
    app.dependency_overrides[get_notification_repository] = (
        lambda: mock_notification_repository
    )
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    try:
        # Arrange - Crear línea de timesheet
        test_date = get_valid_test_date()
        create_data = [
            {
                "name": "Test Timesheet for Review without body",
                "employee_id": 1,
                "project_id": 1,
                "hours": 8.0,
                "date": test_date,
            }
        ]
        create_response = test_client.post("/api/v1/timesheet/", json=create_data)
        assert create_response.status_code == 200
        created_id = create_response.json()[0]["id"]

        # Prepare review request WITHOUT body
        review_request = {
            "approver_mail": "admin@example.com",
            "timesheetline_ids": [created_id],
            # body is intentionally omitted (optional field)
        }

        # Act
        response = test_client.post("/api/v1/timesheet/review", json=review_request)

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Emails enviados correctamente!"

        # Verificar que se llamó al servicio de email con body = None
        assert len(mock_email_service.send_review_mail_calls) == 1
        email_call = mock_email_service.send_review_mail_calls[0]
        assert email_call["body"] is None

        # Cleanup
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
        )
        assert delete_response.status_code == 200

    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_send_review_mail_email_service_exception(
    test_client, mock_email_service, mock_notification_repository, mock_employee_gateway
):
    """Test de integración que verifica el manejo de excepciones del servicio de email."""
    # Mock admin user
    from app.main import app
    from app.shared.security.dependencies import get_current_user
    from app.shared.security.role_enums.dev import Roles
    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Admin role
        }

    # Configure mock to throw exception
    original_send_review_mail = mock_email_service.send_review_mail

    async def failing_send_review_mail(*args, **kwargs):
        raise Exception("Email service error")

    mock_email_service.send_review_mail = failing_send_review_mail

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_common_email_service] = lambda: mock_email_service
    app.dependency_overrides[get_notification_repository] = (
        lambda: mock_notification_repository
    )
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    try:
        # Arrange - Crear línea de timesheet
        test_date = get_valid_test_date()
        create_data = [
            {
                "name": "Test Timesheet for Email Error",
                "employee_id": 1,
                "project_id": 1,
                "hours": 8.0,
                "date": test_date,
            }
        ]
        create_response = test_client.post("/api/v1/timesheet/", json=create_data)
        assert create_response.status_code == 200
        created_id = create_response.json()[0]["id"]

        # Prepare review request
        review_request = {
            "approver_mail": "admin@example.com",
            "body": "This will fail",
            "timesheetline_ids": [created_id],
        }

        # Act
        response = test_client.post("/api/v1/timesheet/review", json=review_request)

        # Assert
        assert response.status_code == 500
        assert "Email service error" in response.json()["detail"]

        # Cleanup
        delete_response = test_client.request(
            "DELETE", "/api/v1/timesheet/", json={"ids": [created_id]}
        )
        assert delete_response.status_code == 200

    finally:
        # Restore original method
        mock_email_service.send_review_mail = original_send_review_mail
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_send_review_mail_empty_timesheetline_ids(
    test_client, mock_email_service, mock_employee_gateway
):
    """Test de integración que verifica el comportamiento con lista vacía de timesheet IDs."""
    # Mock admin user
    from app.main import app
    from app.shared.security.dependencies import get_current_user
    from app.shared.security.role_enums.dev import Roles
    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Admin role
        }

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_common_email_service] = lambda: mock_email_service
    app.dependency_overrides[get_employee_gateway] = lambda: mock_employee_gateway

    try:
        # Arrange
        review_request = {
            "approver_mail": "admin@example.com",
            "body": "No timesheets to review",
            "timesheetline_ids": [],  # Empty list
        }

        # Act
        response = test_client.post("/api/v1/timesheet/review", json=review_request)

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Emails enviados correctamente!"

        # Verificar que NO se llamó al servicio de email (no hay timesheets)
        assert len(mock_email_service.send_review_mail_calls) == 0

    finally:
        app.dependency_overrides.clear()
