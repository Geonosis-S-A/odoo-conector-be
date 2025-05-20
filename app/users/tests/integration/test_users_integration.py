import pytest
from fastapi.testclient import TestClient

# Importá tu app principal y la dependencia de DB
from app.main import app  # O donde esté tu instancia de FastAPI
from app.shared.infra.db.session import get_db

# Importá la fixture de la sesión de test

# --- Fixture para el cliente de test con la DB de test ---


@pytest.fixture
def client(local_db_session):
    # Sobrescribí la dependencia de la DB para que use la sesión de test
    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}  # Limpieza después del test


# --- Tus tests ---


@pytest.mark.integration
def test_sync_users(client):
    """Test de integración que prueba la sincronización de usuarios desde Odoo."""
    response = client.post("/api/v1/users/sync")
    print(response.text)
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
def test_sync_users_creates_new_users(client):
    """Test de integración que verifica que los usuarios nuevos se crean como inactivos."""
    # Act
    response = client.post("/api/v1/users/sync")
    assert response.status_code == 200
    data = response.json()

    # Verificar que los usuarios nuevos están inactivos y tienen el mismo ID que en Odoo
    for user in data:
        assert user["is_active"] is False
        assert user["is_superuser"] is False


@pytest.mark.integration
def test_sync_users_does_not_modify_existing_users(client, local_db_session):
    """Test de integración que verifica que los usuarios existentes no se modifican."""
    # Primera sincronización
    first_sync = client.post("/api/v1/users/sync")
    assert first_sync.status_code == 200
    first_users = first_sync.json()

    # Activar manualmente algunos usuarios y modificar sus datos
    from app.users.infra.db.models import UserModel

    for user in first_users[:2]:  # Modificamos los primeros dos usuarios
        user_model = (
            local_db_session.query(UserModel).filter(UserModel.id == user["id"]).first()
        )
        if user_model:
            user_model.is_active = True
            user_model.is_superuser = True
            user_model.full_name = f"Modified {user_model.full_name}"
    local_db_session.commit()

    # Segunda sincronización
    second_sync = client.post("/api/v1/users/sync")
    assert second_sync.status_code == 200
    second_users = second_sync.json()

    # Verificar que los usuarios modificados mantienen sus cambios
    for user in second_users:
        if user["id"] in [u["id"] for u in first_users[:2]]:
            assert user["is_active"] is True
            assert user["is_superuser"] is True
            assert user["full_name"].startswith("Modified")
        else:
            assert user["is_active"] is False
            assert user["is_superuser"] is False
            assert not user["full_name"].startswith("Modified")


@pytest.mark.integration
def test_sync_users_handles_odoo_connection_error():
    """Test de integración que verifica el manejo de errores de conexión con Odoo."""
    # TODO: Implementar mock de error de conexión con Odoo
    pass
