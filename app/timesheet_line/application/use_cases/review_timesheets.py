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
)


class ReviewTimesheetsUseCase:
    def __init__(
        self,
        employee_gateway: EmployeeGateway,
        timesheet_gateway: TimesheetLineGateway,
        email_service: CommonResendEmailService,
        notification_repository: TimesheetLineNotificationRepository,
    ):
        self.employee_gateway = employee_gateway
        self.timesheet_gateway = timesheet_gateway
        self.email_service = email_service
        self.notification_repository = notification_repository

    async def execute(
        self, timesheet_ids: list[int], approver_mail: str, body: str | None = None
    ) -> bool:
        """Ejecuta el caso de uso para enviar correos de revisión de timesheets.

        Args:
            timesheet_ids: Lista de IDs de las líneas de timesheet a revisar
            approver_mail: Email del aprobador que envía la revisión
            body: Mensaje opcional para incluir en el correo

        Returns:
            bool: True si el envío fue exitoso

        Raises:
            ApproverNotFoundError: Si no se encuentra el approver
            TimesheetNotFoundError: Si no se encuentran las líneas de timesheet
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
                await self.email_service.send_review_mail(
                    receiver_mail,
                    approver_mail,
                    employee_data["timesheets"],
                    body,
                )
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
    