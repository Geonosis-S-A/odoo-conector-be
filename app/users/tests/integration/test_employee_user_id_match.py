import pytest
from fastapi.testclient import TestClient
from sqlmodel import select
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
        # levantar el rol approver del dev.py
        from app.shared.security.role_enums.dev import Roles

        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Rol de administrador
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
def test_sync_single_user_with_user_id(admin_test_client: TestClient, local_db_session):
    """
    Test que verifica la sincronización de un empleado específico que tiene user_id asociado en Odoo.
    Debería actualizar email, nombre y roles del usuario.
    """
    # Arrange
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    # Obtener empleados de Odoo con user_id asociado
    odoo_employees = employee_gateway.get_all_employees_with_user_data()
    employees_with_user = [emp for emp in odoo_employees if emp.get("has_user", False)]

    if not employees_with_user:
        pytest.skip("No hay empleados con user_id asociado en Odoo para probar")

    test_employee = employees_with_user[0]
    employee_id = test_employee["id"]

    # Crear un usuario inicial en la base de datos para simular datos desactualizados
    initial_user = UserModel(
        id=employee_id,
        email="old_email@example.com",  # Email diferente al de Odoo
        full_name="Nombre Desactualizado",  # Nombre diferente al de Odoo
        is_active=True,
        is_superuser=False,
        hashed_password="test_password",
        roles=[1, 2],  # Roles diferentes a los de Odoo
    )
    local_db_session.add(initial_user)
    local_db_session.commit()

    # Act
    response = admin_test_client.post(f"/api/v1/users/sync/{employee_id}")

    # Assert
    assert response.status_code == 200, f"Error en la respuesta: {response.json()}"

    response_data = response.json()

    # Verificar estructura de la respuesta
    assert "success" in response_data
    assert "message" in response_data
    assert "user_updated" in response_data
    assert "changes_made" in response_data

    # Verificar que la sincronización fue exitosa
    assert response_data["success"] is True
    assert response_data["user_updated"] is True

    # Verificar que se reportaron cambios
    changes_made = response_data["changes_made"]
    assert changes_made["has_user_id"] is True
    assert changes_made["employee_id"] == employee_id

    # Verificar que el usuario fue actualizado en la base de datos
    updated_user = local_db_session.exec(
        select(UserModel).where(UserModel.id == employee_id)
    ).first()
    assert updated_user is not None

    # Verificar que los datos se actualizaron desde Odoo
    assert updated_user.email == test_employee["email"]
    assert updated_user.full_name == test_employee["name"]
    assert updated_user.roles == test_employee["roles"]

    # Verificar que se mantuvieron los estados locales
    assert updated_user.is_active is True  # Mantenido del estado original
    assert updated_user.is_superuser is False  # Mantenido del estado original


@pytest.mark.integration
def test_sync_single_user_without_user_id(
    admin_test_client: TestClient, local_db_session
):
    """
    Test que verifica la sincronización de un empleado específico que NO tiene user_id asociado.
    Debería actualizar solo email y nombre, manteniendo los roles existentes.
    """
    # Arrange
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    # Obtener empleados de Odoo sin user_id asociado
    odoo_employees = employee_gateway.get_all_employees_with_user_data()
    employees_without_user = [
        emp for emp in odoo_employees if not emp.get("has_user", False)
    ]

    if not employees_without_user:
        pytest.skip("No hay empleados sin user_id asociado en Odoo para probar")

    test_employee = employees_without_user[0]
    employee_id = test_employee["id"]

    # Verificar que el empleado tiene email válido
    if not test_employee.get("email") or "@" not in test_employee["email"]:
        pytest.skip("El empleado seleccionado no tiene un email válido")

    # Crear un usuario inicial en la base de datos
    original_roles = [3, 4, 5]  # Roles que deben mantenerse
    initial_user = UserModel(
        id=999,  # ID diferente para simular búsqueda por email
        email=test_employee["email"],  # Mismo email para que lo encuentre
        full_name="Nombre Desactualizado",
        is_active=True,
        is_superuser=True,
        hashed_password="test_password",
        roles=original_roles,
    )
    local_db_session.add(initial_user)
    local_db_session.commit()

    # Act
    response = admin_test_client.post(f"/api/v1/users/sync/{employee_id}")

    # Assert
    assert response.status_code == 200, f"Error en la respuesta: {response.json()}"

    response_data = response.json()

    # Verificar que la sincronización fue exitosa
    assert response_data["success"] is True
    assert response_data["user_updated"] is True

    # Verificar que se reportaron cambios
    changes_made = response_data["changes_made"]
    assert changes_made["has_user_id"] is False
    assert changes_made["employee_id"] == employee_id
    assert changes_made["roles"]["changed"] is False  # Los roles no deben cambiar

    # Verificar que el usuario fue actualizado en la base de datos
    updated_user = local_db_session.exec(
        select(UserModel).where(UserModel.email == test_employee["email"])
    ).first()
    assert updated_user is not None

    # Verificar que solo se actualizaron nombre/email, no los roles
    assert updated_user.full_name == test_employee["name"]
    assert updated_user.roles == original_roles  # Se mantuvieron los roles originales

    # Verificar que se mantuvieron los estados locales
    assert updated_user.is_active is True
    assert updated_user.is_superuser is True


@pytest.mark.integration
def test_sync_single_user_no_changes_needed(
    admin_test_client: TestClient, local_db_session
):
    """
    Test que verifica el comportamiento cuando un empleado ya está sincronizado correctamente.
    No debería realizar cambios y reportar que no hay cambios necesarios.
    """
    # Arrange
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    # Obtener un empleado de Odoo que no haya sido usado en otros tests
    odoo_employees = employee_gateway.get_all_employees_with_user_data()
    if len(odoo_employees) < 2:
        pytest.skip("No hay suficientes empleados en Odoo para probar")

    # Usar un empleado diferente para evitar conflictos de ID
    test_employee = None
    for emp in odoo_employees:
        emp_id = emp["id"]
        # Verificar si ya existe un usuario con este ID
        existing = local_db_session.exec(
            select(UserModel).where(UserModel.id == emp_id)
        ).first()
        if not existing:
            test_employee = emp
            break

    if not test_employee:
        # Si todos están ocupados, usar el primero y limpiar
        test_employee = odoo_employees[0]
        existing = local_db_session.exec(
            select(UserModel).where(UserModel.id == test_employee["id"])
        ).first()
        if existing:
            local_db_session.delete(existing)
            local_db_session.commit()

    employee_id = test_employee["id"]

    # Crear un usuario ya sincronizado correctamente
    existing_user = UserModel(
        id=employee_id,
        email=test_employee["email"],
        full_name=test_employee["name"],
        is_active=True,
        is_superuser=False,
        hashed_password="test_password",
        roles=test_employee.get("roles", []),
    )
    local_db_session.add(existing_user)
    local_db_session.commit()

    # Act
    response = admin_test_client.post(f"/api/v1/users/sync/{employee_id}")

    # Assert
    assert response.status_code == 200, f"Error en la respuesta: {response.json()}"

    response_data = response.json()

    # Verificar que no se realizaron cambios
    assert response_data["success"] is True
    assert response_data["user_updated"] is False
    assert "No hay cambios que sincronizar" in response_data["message"]
    assert "current_data" in response_data
    assert response_data.get("changes_made") is None  # No hay cambios


@pytest.mark.integration
def test_sync_single_user_employee_not_found(admin_test_client: TestClient):
    """
    Test que verifica el comportamiento cuando se intenta sincronizar un empleado que no existe en Odoo.
    """
    # Arrange
    non_existent_employee_id = 999999  # ID que probablemente no exista

    # Act
    response = admin_test_client.post(f"/api/v1/users/sync/{non_existent_employee_id}")

    # Assert
    assert response.status_code == 200, f"Error en la respuesta: {response.json()}"

    response_data = response.json()

    # Verificar que se reportó que el empleado no existe
    assert response_data["success"] is False
    assert response_data["user_updated"] is False
    assert "no encontrado en Odoo" in response_data["message"]


@pytest.mark.integration
def test_sync_single_user_user_not_found_locally(
    admin_test_client: TestClient, local_db_session
):
    """
    Test que verifica el comportamiento cuando el empleado existe en Odoo pero no tiene usuario en la base local.
    """
    # Arrange
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    # Obtener un empleado de Odoo
    odoo_employees = employee_gateway.get_all_employees_with_user_data()
    if not odoo_employees:
        pytest.skip("No hay empleados en Odoo para probar")

    test_employee = odoo_employees[0]
    employee_id = test_employee["id"]

    # Asegurarnos de que NO existe un usuario con este ID en la base de datos local
    existing_user = local_db_session.exec(
        select(UserModel).where(UserModel.id == employee_id)
    ).first()
    if existing_user:
        local_db_session.delete(existing_user)
        local_db_session.commit()

    # Si el empleado NO tiene user_id, también debemos asegurar que no haya un usuario con su email
    if not test_employee.get("has_user", False):
        existing_by_email = local_db_session.exec(
            select(UserModel).where(UserModel.email == test_employee["email"])
        ).first()
        if existing_by_email:
            local_db_session.delete(existing_by_email)
            local_db_session.commit()

    # Act
    response = admin_test_client.post(f"/api/v1/users/sync/{employee_id}")

    # Assert
    assert response.status_code == 200, f"Error en la respuesta: {response.json()}"

    response_data = response.json()

    # Verificar que se reportó que el usuario no se encontró localmente
    assert response_data["success"] is False
    assert response_data["user_updated"] is False
    assert "no encontrado en la base de datos local" in response_data["message"]
