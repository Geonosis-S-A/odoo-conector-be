from app.auth.application.services.crypt_service import BcryptPasswordService
from app.auth.infra.email_service import EmailService, get_email_service
from app.auth.infra.password_service import PasswordService


def get_email_service_dependency() -> EmailService:
    """Dependencia para obtener el servicio de email"""
    return get_email_service()


def get_password_service() -> PasswordService:
    """Dependencia para obtener el servicio de contraseñas"""
    return BcryptPasswordService()
