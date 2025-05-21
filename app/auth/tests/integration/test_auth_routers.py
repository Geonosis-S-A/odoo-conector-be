import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.auth.api.routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.mark.integration
def test_login_success():
    """Test de integración: login exitoso con credenciales válidas."""
    # Arrange: Debe existir un usuario válido en la base de datos
    data = {
        "email": "test@example.com",  # Cambia por un usuario real de test
        "password": "password123",  # Cambia por la contraseña real de test
    }
    # Act
    response = client.post("/auth/login", json=data)
    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"
    assert "refresh_token" in response.cookies


@pytest.mark.integration
def test_login_invalid_user():
    """Test de integración: login con usuario inexistente."""
    data = {"email": "noexiste@example.com", "password": "password123"}
    response = client.post("/auth/login", json=data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.integration
def test_login_invalid_password():
    """Test de integración: login con contraseña incorrecta."""
    # Arrange: El usuario debe existir
    data = {
        "email": "test@example.com",  # Cambia por un usuario real de test
        "password": "contraseñaincorrecta",
    }
    response = client.post("/auth/login", json=data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
