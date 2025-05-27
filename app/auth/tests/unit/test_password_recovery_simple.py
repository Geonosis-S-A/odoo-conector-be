import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock
from app.auth.application.use_cases.password_recovery import PasswordRecoveryUseCase
from app.auth.application.dto.password_recovery import RequestOTPDTO, VerifyOTPDTO, ResetPasswordDTO

@pytest.fixture
def mock_user_repository():
    return AsyncMock()

@pytest.fixture
def mock_email_service():
    return AsyncMock()

@pytest.fixture
def mock_password_service():
    service = MagicMock()
    service.hash_password.return_value = "hashed_password"
    return service

@pytest.fixture
def password_recovery_use_case(mock_user_repository, mock_email_service, mock_password_service):
    return PasswordRecoveryUseCase(
        user_repository=mock_user_repository,
        email_service=mock_email_service,
        password_service=mock_password_service
    )

@pytest.mark.asyncio
async def test_request_otp_success(password_recovery_use_case, mock_user_repository, mock_email_service):
    # Arrange
    dto = RequestOTPDTO(email="test@example.com")
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user_repository.get_by_email.return_value = mock_user

    # Act
    result = await password_recovery_use_case.request_otp(dto)

    # Assert
    assert result is True
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_user_repository.save_otp.assert_called_once()
    mock_email_service.send_otp_email.assert_called_once()

@pytest.mark.asyncio
async def test_request_otp_user_not_found(password_recovery_use_case, mock_user_repository):
    # Arrange
    dto = RequestOTPDTO(email="nonexistent@example.com")
    mock_user_repository.get_by_email.return_value = None

    # Act
    result = await password_recovery_use_case.request_otp(dto)

    # Assert
    assert result is False
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_user_repository.save_otp.assert_not_called()

@pytest.mark.asyncio
async def test_verify_otp_success(password_recovery_use_case, mock_user_repository):
    # Arrange
    dto = VerifyOTPDTO(email="test@example.com", code="123456")
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user_repository.get_by_email.return_value = mock_user
    mock_otp = Mock()
    mock_otp.id = 1
    mock_otp.user_id = 1
    mock_otp.code = "123456"
    mock_otp.is_used = False
    mock_user_repository.get_valid_otp.return_value = mock_otp

    # Act
    result = await password_recovery_use_case.verify_otp(dto)

    # Assert
    assert result is True
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_user_repository.get_valid_otp.assert_called_once_with(1, dto.code)

@pytest.mark.asyncio
async def test_verify_otp_invalid(password_recovery_use_case, mock_user_repository):
    # Arrange
    dto = VerifyOTPDTO(email="test@example.com", code="123456")
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user_repository.get_by_email.return_value = mock_user
    mock_user_repository.get_valid_otp.return_value = None

    # Act
    result = await password_recovery_use_case.verify_otp(dto)

    # Assert
    assert result is False
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_user_repository.get_valid_otp.assert_called_once_with(1, dto.code)

@pytest.mark.asyncio
async def test_reset_password_success(password_recovery_use_case, mock_user_repository, mock_password_service):
    # Arrange
    dto = ResetPasswordDTO(
        email="test@example.com",
        code="123456",
        new_password="new_password",
        confirm_password="new_password"
    )
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user_repository.get_by_email.return_value = mock_user
    mock_otp = Mock()
    mock_otp.id = 1
    mock_otp.user_id = 1
    mock_otp.code = "123456"
    mock_otp.is_used = False
    mock_user_repository.get_valid_otp.return_value = mock_otp

    # Act
    result = await password_recovery_use_case.reset_password(dto)

    # Assert
    assert result is True
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_user_repository.get_valid_otp.assert_called_once_with(1, dto.code)
    mock_password_service.hash_password.assert_called_once_with(dto.new_password)
    mock_user_repository.update_password.assert_called_once_with(1, "hashed_password")
    mock_user_repository.mark_otp_as_used.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_reset_password_passwords_dont_match(password_recovery_use_case):
    # Arrange
    dto = ResetPasswordDTO(
        email="test@example.com",
        code="123456",
        new_password="new_password",
        confirm_password="different_password"
    )

    # Act
    result = await password_recovery_use_case.reset_password(dto)

    # Assert
    assert result is False

@pytest.mark.asyncio
async def test_reset_password_invalid_otp(password_recovery_use_case, mock_user_repository):
    # Arrange
    dto = ResetPasswordDTO(
        email="test@example.com",
        code="123456",
        new_password="new_password",
        confirm_password="new_password"
    )
    mock_user = Mock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user_repository.get_by_email.return_value = mock_user
    mock_user_repository.get_valid_otp.return_value = None

    # Act
    result = await password_recovery_use_case.reset_password(dto)

    # Assert
    assert result is False
    mock_user_repository.get_by_email.assert_called_once_with(dto.email)
    mock_user_repository.get_valid_otp.assert_called_once_with(1, dto.code) 