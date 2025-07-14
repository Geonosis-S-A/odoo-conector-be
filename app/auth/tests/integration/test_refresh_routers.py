import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.auth.api.routes import router
from app.shared.infra.db.session import get_db
from app.users.infra.db.models import UserModel
from app.auth.infra.db.models import RefreshTokenModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.auth.infra.auth_service import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Crear una aplicación de FastAPI para pruebas
app = FastAPI()
app.include_router(router)


@pytest.fixture
def client(local_db_session):
    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


def create_refresh_token_for_user(user_id, user_email, user_name, roles):
    payload = {
        "user_id": user_id,
        "user_email": user_email,
        "user_name": user_name,
        "roles": roles,
        "exp": datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


@pytest.mark.integration
def test_refresh_success(client, local_db_session):
    """Test de integración: refresh exitoso con refresh token válido en cookie."""
    # Arrange: Crear usuario y refresh token
    password = "password123"
    hashed_password = pwd_context.hash(password)
    test_user = UserModel(
        id=None,
        email="refresh@example.com",
        full_name="Usuario Refresh",
        hashed_password=hashed_password,
        is_superuser=False,
        is_active=True,
    )
    local_db_session.add(test_user)
    local_db_session.commit()
    local_db_session.refresh(test_user)
    assert test_user.id is not None  # Asegura que id es int

    refresh_token = create_refresh_token_for_user(
        user_id=test_user.id,
        user_email=test_user.email,
        user_name=test_user.full_name,
        roles=["user"],
    )

    # Simular que el token está en la base de datos y no está revocado
    token_model = RefreshTokenModel(
        id=None,
        token=refresh_token,
        user_id=test_user.id,  # test_user.id es int después de commit+refresh
        is_revoked=False,
    )
    local_db_session.add(token_model)
    local_db_session.commit()

    cookies = {"refresh_token": refresh_token}
    response = client.post("/auth/refresh", cookies=cookies)

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"
    assert "user" not in json_data  # El endpoint sólo retorna el token


@pytest.mark.integration
def test_refresh_no_cookie(client):
    """Test de integración: refresh sin cookie debe devolver 401."""
    response = client.post("/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token not found"


@pytest.mark.integration
def test_refresh_invalid_token(client, local_db_session):
    """Test de integración: refresh con token inválido debe devolver 401."""
    # Arrange: Crear usuario pero no guardar el token en la base de datos
    password = "password123"
    hashed_password = pwd_context.hash(password)
    test_user = UserModel(
        id=None,
        email="refreshfail@example.com",
        full_name="Usuario RefreshFail",
        hashed_password=hashed_password,
        is_superuser=False,
        is_active=True,
    )
    local_db_session.add(test_user)
    local_db_session.commit()
    local_db_session.refresh(test_user)
    assert test_user.id is not None  # Asegura que id es int

    # Crear un refresh token válido pero no guardarlo en la base de datos
    refresh_token = create_refresh_token_for_user(
        user_id=test_user.id,
        user_email=test_user.email,
        user_name=test_user.full_name,
        roles=["user"],
    )

    cookies = {"refresh_token": refresh_token}
    response = client.post("/auth/refresh", cookies=cookies)
    assert response.status_code == 401
    # El mensaje puede variar según la lógica interna
    assert (
        "Invalid refresh token" in response.json()["detail"]
        or "Could not validate credentials" in response.json()["detail"]
    )
