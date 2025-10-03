from typing import Protocol, Optional
import resend
from app.core.config import settings
from app.shared.templates.email.email_template_service import email_template_service
from datetime import datetime

from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway


class CommonEmailService(Protocol):
    async def send_support_mail(self, email: str, subject: str, body: str) -> None:
        """Envía un email de soporte al usuario"""
        pass

    async def send_review_mail(
        self,
        user_mail: str,
        timesheet_line_ids: list[int],
        timesheet_line_gateway: TimesheetLineGateway,
        body: Optional[str] = None,
    ) -> None:
        """Envía un email de revisión al usuario"""
        pass




class CommonResendEmailService:
    """Implementación del servicio de email usando Resend"""

    def __init__(self):
        """Inicializa el cliente de Resend con la API key"""
        resend.api_key = settings.RESEND_APIKEY

    async def send_support_mail(
        self, user_name: str, subject: str, body: str, date: datetime
    ) -> None:
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
        approver_mail: str,
        timesheet_lines: list[DetailedTimesheetLine],
        body: Optional[str] = None,
    ) -> None:
        """Envía un email de revisión al usuario usando Resend"""
        try:
            # Obtener todos los timesheet lines

            # Preparar datos para el template
            timesheet_data = []
            for timesheet_line in timesheet_lines:
                timesheet_data.append(
                    {
                        "hours": f"{timesheet_line.hours} hs",
                        "project_name": timesheet_line.project.name
                        if timesheet_line.project
                        else "",
                        "task_name": timesheet_line.task.name
                        if timesheet_line.task
                        else "",
                        "date": timesheet_line.date.strftime("%d/%m/%Y"),
                        "approver_mail": approver_mail,
                    }
                )

            # Usar el servicio de templates para renderizar el email
            html_body = email_template_service.render_template(
                "review_mail",
                BODY=body or "",
                USER_MAIL=user_mail,
                TIMESHEET_COUNT=len(timesheet_lines),
                TIMESHEET_DATA=timesheet_data,
                SHOW_BODY_SECTION="true" if body else "false",
            )

            # Determinar el asunto según la cantidad de registros
            subject = (
                "⚠️ Revisión de registro de horas"
                if len(timesheet_lines) == 1
                else f"⚠️ Revisión de {len(timesheet_lines)} registros de horas"
            )

            # Enviar email usando Resend
            resend.Emails.send(
                {
                    "from": f"Geonosis <{settings.EMAIL_USER}>",
                    "to": user_mail,
                    "subject": subject,
                    "html": html_body,
                }
            )

        except Exception as e:
            raise Exception(f"Error al enviar email con Resend: {str(e)}")
    
    async def send_approved_mail(
        self,
        user_mail: str,
        approver_mail: str,
        timesheet_lines: list[DetailedTimesheetLine],
    ) -> None:
        """Envía un email de aprobación de hojas de horas al usuario usando Resend"""
        try:
            # Obtener todos los timesheet lines

            # Preparar datos para el template
            timesheet_data = []
            for timesheet_line in timesheet_lines:
                timesheet_data.append(
                    {
                        "hours": f"{timesheet_line.hours} hs",
                        "project_name": timesheet_line.project.name
                        if timesheet_line.project
                        else "",
                        "task_name": timesheet_line.task.name
                        if timesheet_line.task
                        else "",
                        "date": timesheet_line.date.strftime("%d/%m/%Y"),
                        "approver_mail": approver_mail,
                    }
                )

            # Usar el servicio de templates para renderizar el email
            html_body = email_template_service.render_template(
                "approved_mail",
                USER_MAIL=user_mail,
                TIMESHEET_COUNT=len(timesheet_lines),
                TIMESHEET_DATA=timesheet_data,
            )

            # Determinar el asunto según la cantidad de registros
            subject = (
                "✅ Aprobación de registro de horas"
                if len(timesheet_lines) == 1
                else f"✅ Aprobación de {len(timesheet_lines)} registros de horas"
            )

            # Enviar email usando Resend
            resend.Emails.send(
                {
                    "from": f"Geonosis <{settings.EMAIL_USER}>",
                    "to": user_mail,
                    "subject": subject,
                    "html": html_body,
                }
            )

        except Exception as e:
            raise Exception(f"Error al enviar email con Resend: {str(e)}")
