import pytest
from app.auth.application.services.crypt_service import BcryptPasswordService


def test_hash_password():
    """Test que la función de hash genera un hash válido"""
    service = BcryptPasswordService()
    password = "test_password"
    hashed = service.hash_password(password)

    assert hashed != password
    assert len(hashed) > 0
    assert isinstance(hashed, str)


def test_verify_password_correct():
    """Test que la verificación funciona con contraseña correcta"""
    service = BcryptPasswordService()
    password = "test_password"
    hashed = service.hash_password(password)

    assert service.verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test que la verificación falla con contraseña incorrecta"""
    service = BcryptPasswordService()
    password = "test_password"
    wrong_password = "wrong_password"
    hashed = service.hash_password(password)

    assert service.verify_password(wrong_password, hashed) is False


def test_hash_different_passwords_different_hashes():
    """Test que contraseñas diferentes generan hashes diferentes"""
    service = BcryptPasswordService()
    password1 = "password1"
    password2 = "password2"

    hash1 = service.hash_password(password1)
    hash2 = service.hash_password(password2)

    assert hash1 != hash2
