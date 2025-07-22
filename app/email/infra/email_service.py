from typing import Protocol, Optional
import resend
from app.core.config import settings
from app.shared.templates.email.email_template_service import email_template_service
from datetime import datetime

from app.timesheet_line.domain.repositories import TimesheetLineGateway


class EmailService(Protocol):
    async def send_support_mail(self, email: str, subject: str, body: str) -> None:
        """Envía un email de soporte al usuario"""
        pass

    async def send_review_mail(
        self,
        user_mail: str,
        body: str,
        timesheet_line_id: int,
        timesheet_line_gateway: TimesheetLineGateway,
    ) -> None:
        """Envía un email de revisión al usuario"""
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
                    "subject": f"{subject} 🚨",
                    "html": html_body,
                }
            )

        except Exception as e:
            raise Exception(f"Error al enviar email con Resend: {str(e)}")
        
    async def send_review_mail(
        self,
        user_mail: str,
        timesheet_line_id: int,
        timesheet_line_gateway: TimesheetLineGateway,
        body: Optional[str] = None,
    ) -> None:
        """Envía un email de revisión al usuario usando Resend"""
        try:
            timesheet_line = timesheet_line_gateway.get_by_id(timesheet_line_id)
            
            if not timesheet_line:
                raise Exception(f"No se encontró el timesheet con id {timesheet_line_id}")
            # Usar el servicio de templates para renderizar el email
            html_body = email_template_service.render_template(
                "review_mail",
                BODY=body or "",
                HOURS= f"{timesheet_line.hours} hs",
                PROJECT_NAME=timesheet_line.project.name if timesheet_line.project else "",
                TASK_NAME=timesheet_line.task.name if timesheet_line.task else "",
                USER_MAIL=user_mail,
                TIMESTAMP=timesheet_line.date.strftime("%d/%m/%Y"),
                SHOW_BODY_SECTION="true" if body else "false",
            )

            # Enviar email usando Resend
            resend.Emails.send(
                {
                    "from": f"Geonosis <{settings.EMAIL_USER}>",
                    "to": user_mail,
                    "subject": "Revisión de horas ⚠️",
                    "html": html_body,
                }
            )

        except Exception as e:
            raise Exception(f"Error al enviar email con Resend: {str(e)}")




def get_email_service() -> ResendEmailService:
    """Factory function para obtener una instancia del servicio de email"""
    return ResendEmailService()
