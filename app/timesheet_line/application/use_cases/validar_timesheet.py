from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetNotFoundError,
    TimesheetValidateError,
    ApproverNotFoundError,
    TimesheetDomainError,
)
from app.email.infra.email_service import CommonResendEmailService
from app.users.domain.repositories import EmployeeGateway
from app.timesheet_line.domain.repositories import TimesheetLineNotificationRepository
import logging


class ValidateTimesheetUseCase:
    def __init__(
        self,
        timesheet_gateway: TimesheetLineGateway,
        email_service: CommonResendEmailService,
        employee_gateway: EmployeeGateway,
        notification_repository: TimesheetLineNotificationRepository,
    ):
        self.timesheet_gateway = timesheet_gateway
        self.email_service = email_service
        self.employee_gateway = employee_gateway
        self.notification_repository = notification_repository

    async def execute(self, timesheet_ids: list[int], approver_mail: str) -> dict:
        """Ejecuta el caso de uso para validar líneas de timesheet.

        Args:
            timesheet_ids: Lista de IDs de las líneas de timesheet a validar
            approver_mail: Email del aprobador que ejecuta la validación

        Returns:
            dict con:
              - validated: lista de IDs validados exitosamente
              - rejected: lista de dicts {employee_name, reason} para los rechazados

        Raises:
            ApproverNotFoundError: Si no se encuentra el approver o no tiene user_id en Odoo
            TimesheetNotFoundError: Si no se encuentran las líneas de timesheet
            TimesheetValidateError: Si hay un error al validar o al enviar emails
        """
        # Verificar que el approver existe
        approver = self.employee_gateway.get_by_email(approver_mail)
        if approver is None:
            raise ApproverNotFoundError(approver_mail)

        # Obtener user_id de Odoo del aprobador
        approver_user_id = self.employee_gateway.get_user_id_by_employee_id(approver.id)
        if approver_user_id is None:
            raise ApproverNotFoundError(approver_mail)

        # Obtener equipo del aprobador
        team = self.timesheet_gateway.get_team_users(approver_user_id, approver.id)
        team_employee_ids = {member["id"] for member in team}
        
        
        logger = logging.getLogger(__name__)
        logger.warning("DEBUG team_employee_ids: %s", [m['id'] for m in team])
        logger.warning("DEBUG approver_user_id: %s approver.id: %s", approver_user_id, approver.id)

        # Verificar que las líneas existen
        existing_timesheets = self.timesheet_gateway.get_by_ids(timesheet_ids)
        if not existing_timesheets or len(existing_timesheets) != len(timesheet_ids):
            raise TimesheetNotFoundError(timesheet_ids)

        # Separar los que puede aprobar de los que no
        allowed_ids: list[int] = []
        rejected: list[dict] = []

        for ts in existing_timesheets:
            if ts.employee_id in team_employee_ids:
                allowed_ids.append(ts.id)
            else:
                employee = self.employee_gateway.get_by_id(ts.employee_id)
                employee_name = employee.full_name if employee else f"ID {ts.employee_id}"
                rejected.append({
                    "employee_name": employee_name,
                    "reason": "No sos el aprobador de horas de este empleado",
                })

        # Validar en Odoo solo los permitidos
        if allowed_ids:
            try:
                success = self.timesheet_gateway.validate(allowed_ids)
                if not success:
                    raise TimesheetValidateError(allowed_ids, "La validación falló")
            except TimesheetDomainError:
                raise
            except Exception as e:
                raise TimesheetValidateError(allowed_ids, str(e))

            # Enviar emails de aprobación
            employees_bucket: dict = {}
            approved_lines = self.timesheet_gateway.get_by_ids(allowed_ids)
            for timesheet_line in approved_lines:
                employee = self.employee_gateway.get_by_id(timesheet_line.employee_id)
                if employee is None:
                    continue
                if employee.email not in employees_bucket:
                    employees_bucket[employee.email] = {
                        "timesheets": [],
                        "employee_id": employee.id,
                    }
                employees_bucket[employee.email]["timesheets"].append(timesheet_line)

            try:
                for receiver_mail, employee_data in employees_bucket.items():
                    await self.email_service.send_approved_mail(
                        receiver_mail,
                        approver_mail,
                        employee_data["timesheets"],
                    )
            except Exception as e:
                raise TimesheetValidateError(
                    allowed_ids, f"Error al enviar emails: {str(e)}"
                )

        return {
            "validated": allowed_ids,
            "rejected": rejected,
        }