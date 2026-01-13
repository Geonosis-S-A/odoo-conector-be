from typing import Protocol, Optional
import resend
from app.core.config import settings
from app.shared.templates.email.email_template_service import email_template_service
from datetime import datetime

from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.email.domain.email_types import TimesheetEmailType


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

    def _prepare_timesheet_data(
        self, 
        timesheet_lines: list[DetailedTimesheetLine], 
        approver_mail: str
    ) -> list[dict]:
        """Prepara los datos de timesheet para los templates (reutilizable)"""
        timesheet_data = []
        for timesheet_line in timesheet_lines:
            timesheet_data.append(
                {
                    "hours": f"{timesheet_line.hours} hs",
                    "project_name": timesheet_line.project.name if timesheet_line.project else "",
                    "task_name": timesheet_line.task.name if timesheet_line.task else "",
                    "date": timesheet_line.date.strftime("%d/%m/%Y"),
                    "approver_mail": approver_mail,
                }
            )
        return timesheet_data

    def _get_template_config(self, email_type: TimesheetEmailType) -> dict:
        """Obtiene la configuración del template según el tipo de email"""
        configs = {
            TimesheetEmailType.APPROVED: {
                "template_name": "approved_mail",
                "subject_single": "✅ Aprobación de registro de horas",
                "subject_multiple": "✅ Aprobación de {count} registros de horas",
            },
            TimesheetEmailType.REVIEW: {
                "template_name": "review_mail",
                "subject_single": "⚠️ Revisión de registro de horas",
                "subject_multiple": "⚠️ Revisión de {count} registros de horas",
            },
            TimesheetEmailType.ELIMINATED: {
                "template_name": "eliminated_mail",
                "subject_single": "🗑️ Eliminación de registro de horas",
                "subject_multiple": "🗑️ Eliminación de {count} registros de horas",
            },
        }
        return configs[email_type]

    async def send_timesheet_mail(
        self,
        email_type: TimesheetEmailType,
        user_mail: str,
        approver_mail: str,
        timesheet_lines: list[DetailedTimesheetLine],
        body: Optional[str] = None,
    ) -> None:
        """Método genérico para enviar emails de timesheet (reutilizable)
        
        Args:
            email_type: Tipo de email (APPROVED, REVIEW, ELIMINATED)
            user_mail: Email del destinatario
            approver_mail: Email del aprobador
            timesheet_lines: Lista de líneas de timesheet
            body: Mensaje opcional para incluir en el correo
        """
        try:
            # Preparar datos comunes
            timesheet_data = self._prepare_timesheet_data(timesheet_lines, approver_mail)
            
            # Obtener configuración del template
            config = self._get_template_config(email_type)
            
            # Preparar contexto para el template
            context = {
                "USER_MAIL": user_mail,
                "TIMESHEET_COUNT": len(timesheet_lines),
                "TIMESHEET_DATA": timesheet_data,
                "SHOW_BODY_SECTION": "true" if body else "false",
            }
            
            # Agregar body solo si existe
            if body:
                context["BODY"] = body
            
            # Renderizar template
            html_body = email_template_service.render_template(
                config["template_name"],
                **context
            )
            
            # Determinar el asunto según la cantidad de registros
            subject = (
                config["subject_single"]
                if len(timesheet_lines) == 1
                else config["subject_multiple"].format(count=len(timesheet_lines))
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

    async def send_review_mail(
        self,
        user_mail: str,
        approver_mail: str,
        timesheet_lines: list[DetailedTimesheetLine],
        body: Optional[str] = None,
    ) -> None:
        """Envía un email de revisión al usuario usando Resend (legacy)"""
        await self.send_timesheet_mail(
            TimesheetEmailType.REVIEW,
            user_mail,
            approver_mail,
            timesheet_lines,
            body,
        )
    
    async def send_approved_mail(
        self,
        user_mail: str,
        approver_mail: str,
        timesheet_lines: list[DetailedTimesheetLine],
    ) -> None:
        """Envía un email de aprobación de hojas de horas al usuario usando Resend (legacy)"""
        await self.send_timesheet_mail(
            TimesheetEmailType.APPROVED,
            user_mail,
            approver_mail,
            timesheet_lines,
        )
