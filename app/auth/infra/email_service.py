from typing import Protocol
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.shared.templates.email.email_template_service import email_template_service


class EmailService(Protocol):
    async def send_otp_email(self, email: str, otp_code: str) -> None:
        """Envía un email con el código OTP al usuario"""
        pass


class SMTPEmailService:
    """Implementación del servicio de email usando SMTP"""

    async def send_otp_email(self, email: str, otp_code: str) -> None:
        """Envía un email con el código OTP al usuario usando SMTP"""
        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_USER
        msg["To"] = email
        msg["Subject"] = "Código de verificación - Geonosis"

        # Usar el servicio de templates para renderizar el email
        html_body = email_template_service.render_template(
            "otp_verification",
            OTP_CODE=otp_code,
        )
        msg.attach(MIMEText(html_body, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            raise Exception(f"Error al enviar email: {str(e)}")


def get_email_service() -> SMTPEmailService:
    """Factory function para obtener una instancia del servicio de email"""
    return SMTPEmailService()
