import pytest
from app.auth.application.services.otp_service import OTPService
from unittest.mock import AsyncMock


def test_generate_otp():
    """Test que el OTP se genera correctamente"""
    # Crear el servicio OTP
    otp_service = OTPService()

    # Generar OTP
    user_id = 1
    new_otp = otp_service.create_otp(user_id)

    # Verificar que el OTP es válido
    assert len(new_otp.code) == 6
    assert new_otp.code.isdigit()
    assert isinstance(new_otp.code, str)
    assert new_otp.user_id == user_id
    assert new_otp.expires_at is not None


def test_generate_multiple_otps_are_different():
    """Test que múltiples OTPs generados son diferentes"""
    # Crear el servicio OTP
    otp_service = OTPService()

    # Generar múltiples OTPs
    user_id = 1
    otps = [otp_service.create_otp(user_id) for _ in range(10)]

    # Extraer solo los códigos para comparar
    codes = [otp.code for otp in otps]

    # Verificar que no todos son iguales (muy improbable que lo sean)
    assert len(set(codes)) > 1


def test_otp_service_internal_generate_code():
    """Test que el método interno de generación de código funciona correctamente"""
    otp_service = OTPService()

    # Generar múltiples códigos usando el método interno
    codes = [otp_service._generate_code() for _ in range(5)]

    # Verificar que todos los códigos tienen el formato correcto
    for code in codes:
        assert len(code) == 6
        assert code.isdigit()
        assert isinstance(code, str)

    # Verificar que no todos los códigos son iguales
    assert len(set(codes)) > 1
