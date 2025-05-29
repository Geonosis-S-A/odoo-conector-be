import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.auth.application.use_cases.password_recovery import PasswordRecoveryUseCase
from app.auth.infra.db.models import OTPModel
from app.auth.application.dto.password_recovery import (
    RequestOTPDTO,
    VerifyOTPDTO,
    ResetPasswordDTO,
)
from app.auth.application.use_cases.exceptions.exceptions import (
    UserNotFound,
    OTPNotFound,
    PasswordNotMatch,
)
from app.users.infra.db.models import UserModel


@pytest.fixture
def mock_user_repository():
    return MagicMock()


@pytest.fixture
def mock_otp_repository():
    repo = MagicMock()
    # save es async, así que necesita ser AsyncMock
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def mock_email_service():
    return AsyncMock()


@pytest.fixture
def mock_password_service():
    service = MagicMock()
    service.hash_password.return_value = "hashed_password"
    return service


@pytest.fixture
def password_recovery_use_case(
    mock_user_repository, mock_otp_repository, mock_email_service, mock_password_service
):
    return PasswordRecoveryUseCase(
        user_repository=mock_user_repository,
        email_service=mock_email_service,
        password_service=mock_password_service,
        otp_repository=mock_otp_repository,
    )


@pytest.mark.asyncio
async def test_request_otp_success(
    password_recovery_use_case,
    mock_user_repository,
    mock_otp_repository,
    mock_email_service,
):
    # Arrange
    dto = RequestOTPDTO(email="test@example.com")
    mock_user_repository.get_by_email.return_value = UserModel(
        id=1,
        email="test@example.com",
        full_name="Test User",
        hashed_password="old_password",
    )

    # Act
    result = await password_recovery_use_case.request_otp(dto)

    # Assert
    assert result is True
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_otp_repository.save.assert_called_once()
    mock_email_service.send_otp_email.assert_called_once()


@pytest.mark.asyncio
async def test_request_otp_user_not_found(
    password_recovery_use_case, mock_user_repository
):
    # Arrange
    dto = RequestOTPDTO(email="nonexistent@example.com")
    mock_user_repository.get_by_email.return_value = None

    # Act & Assert
    with pytest.raises(UserNotFound, match="El usuario no existe"):
        await password_recovery_use_case.request_otp(dto)

    mock_user_repository.get_by_email.assert_called_once_with(dto.email)


@pytest.mark.asyncio
async def test_verify_otp_success(
    password_recovery_use_case, mock_user_repository, mock_otp_repository
):
    # Arrange
    dto = VerifyOTPDTO(email="test@example.com", code="123456")
    mock_user_repository.get_by_email.return_value = UserModel(
        id=1,
        email="test@example.com",
        full_name="Test User",
        hashed_password="old_password",
    )
    mock_otp_repository.get_valid_otp.return_value = OTPModel(
        id=1,
        user_id=1,
        code="123456",
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        is_used=False,
    )

    # Act
    result = await password_recovery_use_case.verify_otp(dto)

    # Assert
    assert result is True
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_otp_repository.get_valid_otp.assert_called_once_with(1, dto.code)


@pytest.mark.asyncio
async def test_verify_otp_invalid(
    password_recovery_use_case, mock_user_repository, mock_otp_repository
):
    # Arrange
    dto = VerifyOTPDTO(email="test@example.com", code="999999")
    mock_user_repository.get_by_email.return_value = UserModel(
        id=1,
        email="test@example.com",
        full_name="Test User",
        hashed_password="old_password",
    )
    mock_otp_repository.get_valid_otp.return_value = None

    # Act & Assert
    with pytest.raises(OTPNotFound, match="El código OTP no es válido"):
        await password_recovery_use_case.verify_otp(dto)

    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_otp_repository.get_valid_otp.assert_called_once_with(1, dto.code)


@pytest.mark.asyncio
async def test_reset_password_success(
    password_recovery_use_case,
    mock_user_repository,
    mock_otp_repository,
    mock_password_service,
):
    # Arrange
    dto = ResetPasswordDTO(
        email="test@example.com",
        code="123456",
        new_password="new_password",
        confirm_password="new_password",
    )
    mock_user_repository.get_by_email.return_value = UserModel(
        id=1,
        email="test@example.com",
        full_name="Test User",
        hashed_password="old_password",
    )
    mock_otp_repository.get_valid_otp.return_value = OTPModel(
        id=1,
        user_id=1,
        code="123456",
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        is_used=False,
    )

    # Act
    result = await password_recovery_use_case.reset_password(dto)

    # Assert
    assert result is True
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_otp_repository.get_valid_otp.assert_called_once_with(1, dto.code)
    mock_password_service.hash_password.assert_called_once_with(dto.new_password)
    mock_user_repository.update_password.assert_called_once_with(1, "hashed_password")
    mock_otp_repository.mark_otp_as_used.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_reset_password_passwords_dont_match(password_recovery_use_case):
    # Arrange
    dto = ResetPasswordDTO(
        email="test@example.com",
        code="123456",
        new_password="new_password",
        confirm_password="different_password",
    )

    # Act & Assert
    with pytest.raises(PasswordNotMatch, match="Las contraseñas no coinciden"):
        await password_recovery_use_case.reset_password(dto)


@pytest.mark.asyncio
async def test_verify_otp_user_not_found(
    password_recovery_use_case, mock_user_repository
):
    # Arrange
    dto = VerifyOTPDTO(email="nonexistent@example.com", code="123456")
    mock_user_repository.get_by_email.return_value = None

    # Act & Assert
    with pytest.raises(UserNotFound, match="El usuario no existe"):
        await password_recovery_use_case.verify_otp(dto)

    mock_user_repository.get_by_email.assert_called_once_with(dto.email)


@pytest.mark.asyncio
async def test_reset_password_user_not_found(
    password_recovery_use_case, mock_user_repository
):
    # Arrange
    dto = ResetPasswordDTO(
        email="nonexistent@example.com",
        code="123456",
        new_password="new_password",
        confirm_password="new_password",
    )
    mock_user_repository.get_by_email.return_value = None

    # Act & Assert
    with pytest.raises(UserNotFound, match="El usuario no existe"):
        await password_recovery_use_case.reset_password(dto)

    mock_user_repository.get_by_email.assert_called_once_with(dto.email)


@pytest.mark.asyncio
async def test_reset_password_invalid_otp(
    password_recovery_use_case, mock_user_repository, mock_otp_repository
):
    # Arrange
    dto = ResetPasswordDTO(
        email="test@example.com",
        code="999999",
        new_password="new_password",
        confirm_password="new_password",
    )
    mock_user_repository.get_by_email.return_value = UserModel(
        id=1,
        email="test@example.com",
        full_name="Test User",
        hashed_password="old_password",
    )
    mock_otp_repository.get_valid_otp.return_value = None

    # Act & Assert
    with pytest.raises(OTPNotFound, match="El código OTP no es válido"):
        await password_recovery_use_case.reset_password(dto)

    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_otp_repository.get_valid_otp.assert_called_once_with(1, dto.code)
