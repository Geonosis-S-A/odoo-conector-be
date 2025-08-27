from app.email.infra.email_service import CommonResendEmailService


def get_common_email_service() -> CommonResendEmailService:
    return CommonResendEmailService()
