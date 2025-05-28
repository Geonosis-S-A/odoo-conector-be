import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.users.api.routers import router
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.users.infra.db.repositories import SQLModelUserRepository
from app.users.infra.db.models import UserModel


app = FastAPI()
app.include_router(router, prefix="/api/v1")
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_repositories():
    """Fixture que configura los repositorios reales."""
    # Configurar Odoo
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    yield {
        "employee_gateway": employee_gateway,
    }


@pytest.mark.integration
def test_employee_user_id_match(test_client):
    """Test que verifica que el ID del empleado coincida con el ID del usuario correspondiente."""
    # Arrange
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    # Obtener empleados de Odoo
    odoo_employees = employee_gateway.all()

    # Act
    # Sincronizar usuarios
    response = test_client.post("/api/v1/users/sync")
    assert response.status_code == 200

    # Obtener usuarios sincronizados
    synced_users = response.json()

    # Assert
    # Crear un diccionario de email -> id para empleados
    employee_email_to_id = {emp.email: emp.id for emp in odoo_employees}

    # Verificar que cada usuario tiene el mismo ID que su empleado correspondiente
    for user in synced_users:
        assert user["email"] in employee_email_to_id, (
            f"Email {user['email']} no encontrado en empleados de Odoo"
        )
        assert user["id"] == employee_email_to_id[user["email"]], (
            f"ID de usuario ({user['id']}) no coincide con ID de empleado ({employee_email_to_id[user['email']]}) para email {user['email']}"
        )
