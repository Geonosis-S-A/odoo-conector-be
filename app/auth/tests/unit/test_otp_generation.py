import pytest
from app.auth.application.use_cases.password_recovery import PasswordRecoveryUseCase
from unittest.mock import AsyncMock


def test_generate_otp():
    """Test que el OTP se genera correctamente"""
    # Crear mocks
    mock_user_repo = AsyncMock()
    mock_email_service = AsyncMock()
    mock_password_service = AsyncMock()
    
    # Crear el caso de uso
    use_case = PasswordRecoveryUseCase(
        user_repository=mock_user_repo,
        email_service=mock_email_service,
        password_service=mock_password_service
    )
    
    # Generar OTP
    otp = use_case.generate_otp()
    
    # Verificar que el OTP es válido
    assert len(otp) == 6
    assert otp.isdigit()
    assert isinstance(otp, str)


def test_generate_multiple_otps_are_different():
    """Test que múltiples OTPs generados son diferentes"""
    # Crear mocks
    mock_user_repo = AsyncMock()
    mock_email_service = AsyncMock()
    mock_password_service = AsyncMock()
    
    # Crear el caso de uso
    use_case = PasswordRecoveryUseCase(
        user_repository=mock_user_repo,
        email_service=mock_email_service,
        password_service=mock_password_service
    )
    
    # Generar múltiples OTPs
    otps = [use_case.generate_otp() for _ in range(10)]
    
    # Verificar que no todos son iguales (muy improbable que lo sean)
    assert len(set(otps)) > 1 