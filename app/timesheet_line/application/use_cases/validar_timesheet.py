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

    async def execute(self, timesheet_ids: list[int], approver_mail: str) -> bool:
        """Ejecuta el caso de uso para validar líneas de timesheet.

        Args:
            timesheet_ids: Lista de IDs de las líneas de timesheet a validar

        Returns:
            bool: True si la validación fue exitosa

        Raises:
            TimesheetNotFoundError: Si no se encuentran las líneas
            TimesheetValidateError: Si hay un error al validar
        """
        # Verificar que las líneas existen
        existing_timesheets = self.timesheet_gateway.get_by_ids(timesheet_ids)
        if not existing_timesheets or len(existing_timesheets) != len(timesheet_ids):
            raise TimesheetNotFoundError(timesheet_ids)

        # Validar en Odoo
        try:
            success = self.timesheet_gateway.validate(timesheet_ids)
            if not success:
                raise TimesheetValidateError(timesheet_ids, "La validación falló")
        except TimesheetDomainError:
            # Re-lanzar excepciones del dominio sin modificar
            raise
        except Exception as e:
            raise TimesheetValidateError(timesheet_ids, str(e))

        # Verificar que el approver existe
        approver = self.employee_gateway.get_by_email(approver_mail)
        if approver is None:
            raise ApproverNotFoundError(approver_mail)

        # Obtener las líneas de timesheet
        timesheet_lines = self.timesheet_gateway.get_by_ids(timesheet_ids)
        if not timesheet_lines:
            raise TimesheetNotFoundError(timesheet_ids)

        # Agrupar timesheets por empleado para enviar los emails
        employees_bucket = {}
        for timesheet_line in timesheet_lines:
            employee = self.employee_gateway.get_by_id(timesheet_line.employee_id)
            if employee is None:
                continue
            if employee.email not in employees_bucket:
                employees_bucket[employee.email] = {
                    "timesheets": [],
                    "employee_id": None,
                }
            employees_bucket[employee.email]["timesheets"].append(timesheet_line)
            employees_bucket[employee.email]["employee_id"] = employee.id

        # Enviar emails
        try:
            for receiver_mail, employee_data in employees_bucket.items():
                await self.email_service.send_approved_mail(
                    receiver_mail,
                    approver_mail,
                    employee_data["timesheets"],
                )
        except Exception as e:
            raise TimesheetValidateError(
                timesheet_ids, f"Error al enviar emails: {str(e)}"
            )

        return True
