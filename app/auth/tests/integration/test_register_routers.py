import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.auth.api.routes import router
from app.shared.infra.db.session import get_db
from app.users.infra.db.models import UserModel

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
def test_register_user(client, local_db_session):
    """Test de integración: registro de un nuevo usuario."""
    # Arrange: Datos del nuevo usuario

    test_user = UserModel(
        id=None,
        email="test@example.com",
        full_name="Usuario Test",
        hashed_password="",
        is_superuser=False,
        is_active=False,
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
    assert not saved_user.is_active, "El usuario no está activo"

    new_user_data = {
        "email": "test@example.com",
        "password": "newpassword123",
    }

    # Act: Registrar nuevo usuario
    response = client.post("/auth/register", json=new_user_data)

    # Assert: Verificar que el registro fue exitoso
    assert response.status_code == 200, "El registro no fue exitoso"
    json_data = response.json()
    assert "id" in json_data, "El ID del usuario no está en la respuesta"
    assert json_data["email"] == new_user_data["email"], "El email no coincide"
    assert json_data["is_active"], "El usuario no está activo"

    # Verificar que el usuario se guardó en la base de datos
    saved_user = (
        local_db_session.query(UserModel)
        .filter(UserModel.email == new_user_data["email"])
        .first()
    )
    assert saved_user is not None, "El usuario no se guardó en la base de datos"
    assert saved_user.email == new_user_data["email"], (
        "El email del usuario guardado no coincide"
    )
    assert saved_user.is_active, "El usuario guardado no está activo"
