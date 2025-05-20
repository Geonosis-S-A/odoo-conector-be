import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.users.api.routers import router
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.users.infra.db.repositories import SQLModelUserRepository
from app.shared.infra.db.session import SessionLocal
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

    # Configurar Base de datos
    db = SessionLocal()
    user_repository = SQLModelUserRepository(db)

    yield {
        "employee_gateway": employee_gateway,
        "user_repository": user_repository,
        "db": db,
    }

    # Limpieza después de cada test
    _cleanup_test_data(db)


def _cleanup_test_data(db):
    """Limpia los datos de prueba de la base de datos."""
    db.query(UserModel).delete()
    db.commit()
    db.close()


@pytest.mark.integration
def test_sync_users():
    """Test de integración que prueba la sincronización de usuarios desde Odoo."""
    # Act
    response = client.post("/api/v1/users/sync")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Verificar la estructura de los datos
    if len(data) > 0:
        assert all(isinstance(item["id"], int) for item in data)
        assert all(isinstance(item["email"], str) for item in data)
        assert all(isinstance(item["full_name"], str) for item in data)
        assert all(isinstance(item["is_active"], bool) for item in data)
        assert all(isinstance(item["is_superuser"], bool) for item in data)


@pytest.mark.integration
def test_sync_users_creates_new_users():
    """Test de integración que verifica que los usuarios nuevos se crean como inactivos."""
    # Arrange - Obtener empleados de Odoo para comparar IDs
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)
    odoo_employees = employee_gateway.all()
    odoo_employee_ids = {emp.id for emp in odoo_employees}

    # Act
    response = client.post("/api/v1/users/sync")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Verificar que los usuarios nuevos están inactivos y tienen el mismo ID que en Odoo
    for user in data:
        assert user["id"] in odoo_employee_ids
        assert user["is_active"] is False
        assert user["is_superuser"] is False


@pytest.mark.integration
def test_sync_users_does_not_modify_existing_users():
    """Test de integración que verifica que los usuarios existentes no se modifican."""
    # Arrange - Primera sincronización
    first_sync = client.post("/api/v1/users/sync")
    assert first_sync.status_code == 200
    first_users = first_sync.json()

    # Activar manualmente algunos usuarios y modificar sus datos
    db = SessionLocal()
    for user in first_users[:2]:  # Modificamos los primeros dos usuarios
        user_model = db.query(UserModel).filter(UserModel.id == user["id"]).first()
        if user_model:
            user_model.is_active = True
            user_model.is_superuser = True
            user_model.full_name = f"Modified {user_model.full_name}"
    db.commit()
    db.close()

    # Act - Segunda sincronización
    second_sync = client.post("/api/v1/users/sync")
    assert second_sync.status_code == 200
    second_users = second_sync.json()

    # Assert
    assert len(first_users) == len(second_users)

    # Verificar que los usuarios modificados mantienen sus cambios
    for user in second_users:
        if user["id"] in [u["id"] for u in first_users[:2]]:
            # Los usuarios modificados deben mantener sus cambios
            assert user["is_active"] is True
            assert user["is_superuser"] is True
            assert user["full_name"].startswith("Modified")
        else:
            # Los demás usuarios deben estar inactivos
            assert user["is_active"] is False
            assert user["is_superuser"] is False
            assert not user["full_name"].startswith("Modified")


@pytest.mark.integration
def test_sync_users_handles_odoo_connection_error():
    """Test de integración que verifica el manejo de errores de conexión con Odoo."""
    # TODO: Implementar mock de error de conexión con Odoo
    pass
