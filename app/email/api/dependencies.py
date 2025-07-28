from app.email.infra.email_service import CustomResendEmailService


def get_email_service_dependency() -> CustomResendEmailService:
    """Dependencia para obtener el servicio de email"""
    return CustomResendEmailService()
