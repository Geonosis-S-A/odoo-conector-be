import pytest
from fastapi.testclient import TestClient
from app.users.infra.db.models import UserModel
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.shared.security.dependencies import get_current_user


@pytest.fixture(scope="function")
def admin_test_client(local_db_session):
    """
    Fixture que proporciona un TestClient configurado con un usuario admin.
    """
    from app.main import app
    from app.shared.infra.db.session import get_db

    # Override para la base de datos
    def override_get_db():
        yield local_db_session

    # Override para un usuario administrador
    async def override_get_current_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [30],  # Rol de administrador
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


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
def test_employee_user_id_match(admin_test_client: TestClient, local_db_session):
    """Test que verifica que el ID del empleado coincida con el ID del usuario correspondiente."""
    # Arrange
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    # Obtener empleados de Odoo
    odoo_employees = employee_gateway.get_all_employees_with_user_data()
    assert odoo_employees, "No se pudieron obtener empleados de Odoo para el test"

    # Act
    # Sincronizar usuarios
    response = admin_test_client.post("/api/v1/users/sync")

    # Debug: Imprimir la respuesta en caso de error
    if response.status_code != 200:
        print(f"Error response: {response.status_code} - {response.json()}")

    assert response.status_code == 200, (
        f"La sincronización inicial falló: {response.json()}"
    )

    # Obtener usuarios sincronizados desde la base de datos local
    synced_users = local_db_session.query(UserModel).all()

    # Assert
    # Solo verificar si hay usuarios sincronizados
    if synced_users:
        # Crear un diccionario de email -> id para empleados de Odoo que tienen usuarios
        employee_email_to_id = {
            emp["email"]: emp["id"]
            for emp in odoo_employees
            if emp.get("has_user", False) and emp.get("email")
        }

        # Verificar que cada usuario tiene el mismo ID que su empleado correspondiente
        for user in synced_users:
            if user.email in employee_email_to_id:
                assert user.id == employee_email_to_id[user.email], (
                    f"El ID del usuario {user.id} no coincide con el ID del empleado en Odoo"
                )
    else:
        # Si no hay usuarios sincronizados, solo verificar que la respuesta sea exitosa
        response_data = response.json()
        assert response_data.get("success", False), "La sincronización debe ser exitosa"
        print(f"Sincronización completada. Resultado: {response_data}")
