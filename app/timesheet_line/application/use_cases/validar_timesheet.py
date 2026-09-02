from typing import Optional

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
from app.team.domain.repositories import TeamRepository


class ValidateTimesheetUseCase:
    def __init__(
        self,
        timesheet_gateway: TimesheetLineGateway,
        email_service: CommonResendEmailService,
        employee_gateway: EmployeeGateway,
        notification_repository: TimesheetLineNotificationRepository,
        team_repository: Optional[TeamRepository] = None,
    ):
        self.timesheet_gateway = timesheet_gateway
        self.email_service = email_service
        self.employee_gateway = employee_gateway
        self.notification_repository = notification_repository
        self.team_repository = team_repository

    async def execute(
        self,
        timesheet_ids: list[int],
        approver_mail: str,
        is_admin: bool = True,
        validator_employee_id: Optional[int] = None,
    ) -> bool:
        # Verificar que las líneas existen
        existing_timesheets = self.timesheet_gateway.get_by_ids(timesheet_ids)
        if not existing_timesheets or len(existing_timesheets) != len(timesheet_ids):
            raise TimesheetNotFoundError(timesheet_ids)

        # Si no es admin, verificar que todas las líneas pertenecen a empleados de su equipo
        if not is_admin and validator_employee_id is not None and self.team_repository:
            team_employee_ids = self.team_repository.get_team_member_ids_by_any_leader(
                validator_employee_id
            )
            timesheet_employee_ids = {t.employee_id for t in existing_timesheets}
            outside = timesheet_employee_ids - set(team_employee_ids)
            if outside:
                raise TimesheetValidateError(
                    timesheet_ids,
                    f"No tienes permiso para validar horas de empleados fuera de tu equipo: {outside}",
                )

        # Verificar que el approver existe antes de validar
        approver = self.employee_gateway.get_by_email(approver_mail)
        if approver is None:
            raise ApproverNotFoundError(approver_mail)

        # Quien realmente ejecuta la validación (usuario Geo autenticado); si no
        # llega, se cae al approver resuelto por email.
        approved_by_id = validator_employee_id or approver.id

        # Validar en Odoo
        try:
            success = self.timesheet_gateway.validate(timesheet_ids, approved_by_id)
            if not success:
                raise TimesheetValidateError(timesheet_ids, "La validación falló")
        except TimesheetDomainError:
            raise
        except Exception as e:
            raise TimesheetValidateError(timesheet_ids, str(e))

        # Obtener líneas con estado actualizado post-validación
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
