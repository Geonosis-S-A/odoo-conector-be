import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.auth.api.routes import router
from app.shared.infra.db.session import get_db
from app.users.infra.db.models import UserModel
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Crear una aplicación de FastAPI para pruebas
app = FastAPI()
app.include_router(router)


@pytest.fixture
def client(local_db_session):
    # Sobrescribí la dependencia de la DB para que use la sesión de test
    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}  # Limpieza después del test


@pytest.mark.integration
def test_login_success(client, local_db_session):
    """Test de integración: login exitoso con credenciales válidas."""
    # Arrange: Crear usuario de prueba
    password = "password123"
    hashed_password = pwd_context.hash(password)

    test_user = UserModel(
        id=None,
        email="test@example.com",
        full_name="Usuario Test",
        hashed_password=hashed_password,
        is_superuser=False,
        is_active=True,
    )
    local_db_session.add(test_user)
    local_db_session.commit()

    # Verificar que el usuario se guardó correctamente
    saved_user = (
        local_db_session.query(UserModel)
        .filter(UserModel.email == "test@example.com")
        .first()
    )
    assert saved_user is not None, "El usuario no se guardó en la base de datos"
    assert saved_user.email == "test@example.com", "El email no coincide"
    assert saved_user.is_active, "El usuario no está activo"

    data = {
        "email": "test@example.com",
        "password": password,
    }
    # Act
    response = client.post("/auth/login", json=data)

    # Debug: Imprimir la respuesta en caso de error
    if response.status_code != 200:
        print(f"Error response: {response.json()}")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    print("RESPUESTA DEL LOGIN: " + str(json_data))
    assert "access_token" in json_data
    assert "user" in json_data
    assert json_data["user"]["user_id"] == saved_user.id
    assert json_data["user"]["user_name"] == saved_user.full_name
    assert json_data["user"]["user_email"] == saved_user.email
    assert json_data["user"]["roles"] == ["user"]


@pytest.mark.integration
def test_login_invalid_user(client):
    """Test de integración: login con usuario inexistente."""
    data = {"email": "noexiste@example.com", "password": "password123"}
    response = client.post("/auth/login", json=data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
def test_login_invalid_password(client, local_db_session):
    """Test de integración: login con contraseña incorrecta."""
    # Arrange: Crear usuario de prueba
    password = "password123"
    hashed_password = pwd_context.hash(password)

    test_user = UserModel(
        id=None,
        email="testana@example.com",
        full_name="Usuario Test",
        hashed_password=hashed_password,
        is_superuser=False,
        is_active=True,
    )
    local_db_session.add(test_user)
    local_db_session.commit()

    data = {
        "email": "test@example.com",
        "password": "contraseñaincorrecta",
    }
    response = client.post("/auth/login", json=data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
def test_login_inactive_user(client, local_db_session):
    """Test de integración: login con usuario inactivo."""
    # Arrange: Crear usuario de prueba inactivo
    password = "password123"
    hashed_password = pwd_context.hash(password)

    inactive_user = UserModel(
        id=None,
        email="inactive@example.com",
        full_name="Usuario Inactivo",
        hashed_password=hashed_password,
        is_superuser=False,
        is_active=False,  # Usuario inactivo
    )
    local_db_session.add(inactive_user)
    local_db_session.commit()

    data = {
        "email": "inactive@example.com",
        "password": password,
    }
    # Act
    response = client.post("/auth/login", json=data)

    # Assert
    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user"
