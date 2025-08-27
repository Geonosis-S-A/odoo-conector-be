from app.auth.application.services.crypt_service import BcryptPasswordService
from app.auth.infra.email_service import AuthEmailService, get_auth_email_service
from app.auth.infra.password_service import PasswordService


def get_auth_email_service_dependency() -> AuthEmailService:
    """Dependencia para obtener el servicio de email"""
    return get_auth_email_service()


def get_password_service() -> PasswordService:
    """Dependencia para obtener el servicio de contraseñas"""
    return BcryptPasswordService()
