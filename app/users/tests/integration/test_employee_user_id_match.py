import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.users.api.routers import router
from app.shared.infra.db.session import get_db
from app.users.infra.db.models import UserModel
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway


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
def test_employee_user_id_match(test_client: TestClient, local_db_session):
    """Test que verifica que el ID del empleado coincida con el ID del usuario correspondiente."""
    # Arrange
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    # Obtener empleados de Odoo
    odoo_employees = employee_gateway.get_all_users_with_roles()
    assert odoo_employees, "No se pudieron obtener empleados de Odoo para el test"

    # Act
    # Sincronizar usuarios
    response = test_client.post("/api/v1/users/sync")
    assert response.status_code == 200, "La sincronización inicial falló"

    # Obtener usuarios sincronizados desde la base de datos local
    synced_users = local_db_session.query(UserModel).all()
    assert synced_users, (
        "No se encontraron usuarios en la base de datos después de la sincronización"
    )

    # Assert
    # Crear un diccionario de email -> id para empleados de Odoo
    employee_email_to_id = {emp["email"]: emp["id"] for emp in odoo_employees}

    # Verificar que cada usuario tiene el mismo ID que su empleado correspondiente
    for user in synced_users:
        assert user.email in employee_email_to_id, (
            f"Email {user.email} del usuario local no encontrado en empleados de Odoo"
        )
        assert user.id == employee_email_to_id[user.email], (
            f"El ID del usuario {user.id} no coincide con el ID del empleado en Odoo"
        )
