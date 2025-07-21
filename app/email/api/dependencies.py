from app.email.infra.email_service import ResendEmailService


def get_email_service_dependency() -> ResendEmailService:
    """Dependencia para obtener el servicio de email"""
    return ResendEmailService()