from typing import Optional

from app.team.application.team_access import TeamAccessService
from app.timesheet_line.domain.repositories import (
    TimesheetLineGateway,
    TimesheetLineNotificationRepository,
)
from app.users.domain.repositories import EmployeeGateway
from app.email.infra.email_service import CommonResendEmailService
from app.timesheet_line.domain.models import CreateTimesheetLineNotification
from app.timesheet_line.application.excepctions.exceptions import (
    ApproverNotFoundError,
    TimesheetNotFoundError,
    TimesheetReviewError,
    TimesheetReviewForbiddenError,
)
from app.email.domain.email_types import TimesheetEmailType


class ReviewTimesheetsUseCase:
    def __init__(
        self,
        employee_gateway: EmployeeGateway,
        timesheet_gateway: TimesheetLineGateway,
        email_service: CommonResendEmailService,
        notification_repository: TimesheetLineNotificationRepository,
        team_access: Optional[TeamAccessService] = None,
    ):
        self.employee_gateway = employee_gateway
        self.timesheet_gateway = timesheet_gateway
        self.email_service = email_service
        self.notification_repository = notification_repository
        self.team_access = team_access

    async def execute(
        self,
        timesheet_ids: list[int],
        approver_mail: str,
        body: str | None = None,
        email_type: TimesheetEmailType = TimesheetEmailType.REVIEW,
        reviewer_employee_id: Optional[int] = None,
    ) -> bool:
        """Ejecuta el caso de uso para enviar correos de revisión/eliminación de timesheets.

        Args:
            timesheet_ids: Lista de IDs de las líneas de timesheet a revisar/eliminar
            approver_mail: Email del aprobador que envía la revisión/eliminación
            body: Mensaje opcional para incluir en el correo
            email_type: Tipo de email a enviar (REVIEW o ELIMINATED)
            reviewer_employee_id: Empleado que rechaza. Si se informa junto con
                ``team_access``, cada línea debe poder ser validada por él
                (gerente o PM del proyecto de la línea): tener el rol approver
                no alcanza para rechazar horas de proyectos ajenos.

        Returns:
            bool: True si el envío fue exitoso

        Raises:
            ApproverNotFoundError: Si no se encuentra el approver
            TimesheetNotFoundError: Si no se encuentran las líneas de timesheet
            TimesheetReviewForbiddenError: Si alguna línea está fuera de su alcance
            TimesheetReviewError: Si hay un error al enviar los correos
        """
        # Verificar que el approver existe
        approver = self.employee_gateway.get_by_email(approver_mail)
        if approver is None:
            raise ApproverNotFoundError(approver_mail)
        approver_id = approver.id

        # Obtener las líneas de timesheet
        timesheet_lines = self.timesheet_gateway.get_by_ids(timesheet_ids)
        if not timesheet_lines:
            raise TimesheetNotFoundError(timesheet_ids)

        # Misma autoridad por línea que validar y borrar (consulta Odoo en el
        # momento, sin caché): solo los proyectos que gerencia o de los que es PM.
        if reviewer_employee_id is not None and self.team_access is not None:
            authority = self.team_access.lines_authority(
                reviewer_employee_id,
                [(t.employee_id, t.project.id) for t in timesheet_lines],
            )
            forbidden = sorted(
                t.id
                for t in timesheet_lines
                if not authority.get((t.employee_id, t.project.id), False)
            )
            if forbidden:
                raise TimesheetReviewForbiddenError(forbidden)

        # Agrupar timesheets por empleado
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

        # Enviar correos y crear notificaciones
        try:
            for receiver_mail, employee_data in employees_bucket.items():
                await self.email_service.send_timesheet_mail(
                    email_type,
                    receiver_mail,
                    approver_mail,
                    employee_data["timesheets"],
                    body,
                )
                # Solo crear notificaciones si es REVIEW (no para ELIMINATED)
                if email_type == TimesheetEmailType.REVIEW:
                    for timesheet_line in employee_data["timesheets"]:
                        self.notification_repository.create(
                            CreateTimesheetLineNotification(
                                timesheet_line_id=timesheet_line.id,
                                approver_id=approver_id,
                                receiver_id=employee_data["employee_id"],
                            )
                        )

            return True
        except Exception as e:
            raise TimesheetReviewError(str(e))
    