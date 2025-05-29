import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.auth.api.routes import router
from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.users.infra.db.models import UserModel
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Crear una aplicación de FastAPI para pruebas
app = FastAPI()
app.include_router(router)


@pytest.fixture
def client_with_user_1(local_db_session):
    def override_get_db():
        yield local_db_session

    def override_get_current_user():
        return {
            "user_id": 1,
            "user_email": "test1@example.com",
            "user_name": "Test User 1",
            "roles": ["user"],
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


@pytest.fixture
def client_with_user_2(local_db_session):
    def override_get_db():
        yield local_db_session

    def override_get_current_user():
        return {
            "user_id": 2,
            "user_email": "test2@example.com",
            "user_name": "Test User 2",
            "roles": ["user"],
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


@pytest.fixture
def client_with_user_3(local_db_session):
    def override_get_db():
        yield local_db_session

    def override_get_current_user():
        return {
            "user_id": 3,
            "user_email": "test3@example.com",
            "user_name": "Test User 3",
            "roles": ["user"],
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


@pytest.fixture
def client_with_user_4(local_db_session):
    def override_get_db():
        yield local_db_session

    def override_get_current_user():
        return {
            "user_id": 4,
            "user_email": "test4@example.com",
            "user_name": "Test User 4",
            "roles": ["user"],
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


@pytest.fixture
def client_with_user_999(local_db_session):
    def override_get_db():
        yield local_db_session

    def override_get_current_user():
        return {
            "user_id": 999,  # Usuario que no existe en DB
            "user_email": "nonexistent@example.com",
            "user_name": "Non Existent User",
            "roles": ["user"],
        }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


@pytest.mark.integration
def test_change_password_success(client_with_user_1, local_db_session):
    """Test de integración: cambio exitoso de contraseña."""
    # Arrange: Crear usuario de prueba
    current_password = "old_password123"
    hashed_current_password = pwd_context.hash(current_password)

    test_user = UserModel(
        id=1,
        email="test1@example.com",
        full_name="Test User 1",
        hashed_password=hashed_current_password,
        is_superuser=False,
        is_active=True,
    )
    local_db_session.add(test_user)
    local_db_session.commit()

    data = {
        "current_password": current_password,
        "new_password": "new_password123",
    }

    # Act
    response = client_with_user_1.put("/auth/change-password", json=data)

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["message"] == "Contraseña cambiada exitosamente"

    # Verificar que la contraseña se actualizó en la base de datos
    local_db_session.refresh(test_user)
    assert pwd_context.verify("new_password123", test_user.hashed_password)


@pytest.mark.integration
def test_change_password_incorrect_current_password(
    client_with_user_2, local_db_session
):
    """Test de integración: cambio de contraseña con contraseña actual incorrecta."""
    # Arrange: Crear usuario de prueba
    current_password = "old_password123"
    hashed_current_password = pwd_context.hash(current_password)

    test_user = UserModel(
        id=2,
        email="test2@example.com",
        full_name="Test User 2",
        hashed_password=hashed_current_password,
        is_superuser=False,
        is_active=True,
    )
    local_db_session.add(test_user)
    local_db_session.commit()

    data = {
        "current_password": "wrong_password",
        "new_password": "new_password123",
    }

    # Act
    response = client_with_user_2.put("/auth/change-password", json=data)

    # Assert
    assert response.status_code == 400
    json_data = response.json()
    assert "Contraseña actual incorrecta" in json_data["detail"]


@pytest.mark.integration
def test_change_password_same_as_current(client_with_user_3, local_db_session):
    """Test de integración: cambio de contraseña con nueva contraseña igual a la actual."""
    # Arrange: Crear usuario de prueba
    current_password = "same_password123"
    hashed_current_password = pwd_context.hash(current_password)

    test_user = UserModel(
        id=3,
        email="test3@example.com",
        full_name="Test User 3",
        hashed_password=hashed_current_password,
        is_superuser=False,
        is_active=True,
    )
    local_db_session.add(test_user)
    local_db_session.commit()

    data = {
        "current_password": current_password,
        "new_password": current_password,  # Misma contraseña
    }

    # Act
    response = client_with_user_3.put("/auth/change-password", json=data)

    # Assert
    assert response.status_code == 400
    json_data = response.json()
    assert "La nueva contraseña debe ser diferente a la actual" in json_data["detail"]


@pytest.mark.integration
def test_change_password_user_not_found(client_with_user_999, local_db_session):
    """Test de integración: cambio de contraseña con usuario inexistente."""
    # Arrange: No crear usuario, el mock devuelve user_id=999 pero no existe en DB
    data = {
        "current_password": "any_password",
        "new_password": "new_password123",
    }

    # Act
    response = client_with_user_999.put("/auth/change-password", json=data)

    # Assert
    assert response.status_code == 404
    json_data = response.json()
    assert "Usuario no encontrado" in json_data["detail"]


@pytest.mark.integration
def test_change_password_inactive_user(client_with_user_4, local_db_session):
    """Test de integración: cambio de contraseña con usuario inactivo."""
    # Arrange: Crear usuario inactivo
    current_password = "old_password123"
    hashed_current_password = pwd_context.hash(current_password)

    test_user = UserModel(
        id=4,
        email="test4@example.com",
        full_name="Test User 4",
        hashed_password=hashed_current_password,
        is_superuser=False,
        is_active=False,  # Usuario inactivo
    )
    local_db_session.add(test_user)
    local_db_session.commit()

    data = {
        "current_password": current_password,
        "new_password": "new_password123",
    }

    # Act
    response = client_with_user_4.put("/auth/change-password", json=data)

    # Assert
    assert response.status_code == 401
    json_data = response.json()
    assert "Usuario inactivo" in json_data["detail"]
