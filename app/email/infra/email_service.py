from typing import Protocol
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import resend
from app.core.config import settings
from app.shared.templates.email.email_template_service import email_template_service
from datetime import datetime

class EmailService(Protocol):
    async def send_support_mail(self, email: str, subject: str, body: str) -> None:
        """Envía un email de soporte al usuario"""
        pass


class ResendEmailService:
    """Implementación del servicio de email usando Resend"""

    def __init__(self):
        """Inicializa el cliente de Resend con la API key"""
        resend.api_key = settings.RESEND_APIKEY

    async def send_support_mail(self, user_name: str, subject: str, body: str, date: datetime) -> None:
        """Envía un email de soporte al usuario usando Resend"""
        try:
            # Formatear la fecha para mostrar en el email
            formatted_date = date.strftime("%d/%m/%Y")
            
            # Usar el servicio de templates para renderizar el email
            html_body = email_template_service.render_template(
                "support_mail",
                SUBJECT=subject,
                BODY=body,
                USER_NAME=user_name,
                TIMESTAMP=formatted_date,
            )

            # Enviar email usando Resend
            resend.Emails.send(
                {
                    "from": f"Geonosis <{settings.EMAIL_USER}>",
                    "to": "ia.sf@geonosis.com.ar",
                    "subject": subject,
                    "html": html_body,
                }
            )

        except Exception as e:
            raise Exception(f"Error al enviar email con Resend: {str(e)}")




def get_email_service() -> ResendEmailService:
    """Factory function para obtener una instancia del servicio de email"""
    return ResendEmailService()
