import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from app.auth.application.services.crypt_service import BcryptPasswordService
from app.main import app
from app.users.infra.db.models import UserModel
from app.auth.infra.db.models import OTPModel
from app.auth.infra.db.repositories import SQLModelUserRepository
from app.auth.api.dependencies import SMTPEmailService
from app.auth.application.use_cases.password_recovery import PasswordRecoveryUseCase
from app.shared.infra.db.session import get_db
import datetime


# Configuración de la base de datos de prueba
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_db] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="user_repository")
def user_repository_fixture(session: Session):
    return SQLModelUserRepository(session)


@pytest.fixture(name="email_service")
def email_service_fixture():
    return SMTPEmailService()


@pytest.fixture(name="password_service")
def password_service_fixture():
    return BcryptPasswordService()


@pytest.fixture(name="password_recovery_use_case")
def password_recovery_use_case_fixture(
    user_repository, email_service, password_service
):
    return PasswordRecoveryUseCase(user_repository, email_service, password_service)


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session, password_service: BcryptPasswordService):
    user = UserModel(
        id=None,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        hashed_password=password_service.hash_password("old_password"),
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_password_recovery_flow(
    client: TestClient,
    session: Session,
    test_user: UserModel,
    password_recovery_use_case: PasswordRecoveryUseCase,
):
    # 1. Solicitar OTP
    response = client.post(
        "/api/v1/auth/password-recovery/request", json={"email": test_user.email}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "OTP sent successfully"}

    # Verificar que se creó el OTP en la base de datos
    statement = select(OTPModel).where(
        OTPModel.user_id == test_user.id, OTPModel.is_used == False
    )
    otp = session.exec(statement).first()
    assert otp is not None
    assert len(otp.code) == 6

    # 2. Verificar OTP
    response = client.post(
        "/api/v1/auth/password-recovery/verify",
        json={"email": test_user.email, "code": otp.code},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "OTP verified successfully"}

    # 3. Resetear contraseña
    new_password = "new_secure_password"
    response = client.post(
        "/api/v1/auth/password-recovery/reset",
        json={
            "email": test_user.email,
            "code": otp.code,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset successfully"}

    # Verificar que el OTP está marcado como usado
    session.refresh(otp)
    assert otp.is_used is True

    # Verificar que la contraseña se actualizó
    session.refresh(test_user)
    assert test_user.hashed_password != "old_password"


@pytest.mark.asyncio
async def test_password_recovery_invalid_email(
    client: TestClient, password_recovery_use_case: PasswordRecoveryUseCase
):
    response = client.post(
        "/api/v1/auth/password-recovery/request",
        json={"email": "nonexistent@example.com"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


@pytest.mark.asyncio
async def test_password_recovery_invalid_otp(
    client: TestClient,
    test_user: UserModel,
    password_recovery_use_case: PasswordRecoveryUseCase,
    session: Session,
):
    response = client.post(
        "/api/v1/auth/password-recovery/verify",
        json={"email": test_user.email, "code": "000000"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid OTP"}


@pytest.mark.asyncio
async def test_password_recovery_passwords_dont_match(
    client: TestClient,
    test_user: UserModel,
    session: Session,
    password_recovery_use_case: PasswordRecoveryUseCase,
):
    # Primero solicitar OTP
    response = client.post(
        "/api/v1/auth/password-recovery/request", json={"email": test_user.email}
    )
    assert response.status_code == 200

    # Obtener el OTP de la base de datos
    statement = select(OTPModel).where(
        OTPModel.user_id == test_user.id, OTPModel.is_used == False
    )
    otp = session.exec(statement).first()
    assert otp is not None  # Verificar que el OTP existe

    # Intentar resetear con contraseñas diferentes
    response = client.post(
        "/api/v1/auth/password-recovery/reset",
        json={
            "email": test_user.email,
            "code": otp.code,
            "new_password": "new_password",
            "confirm_password": "different_password",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Passwords do not match"}
