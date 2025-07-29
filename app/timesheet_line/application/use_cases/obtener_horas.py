from typing import List
from datetime import date

from app.timesheet_line.api.schemas import TimesheetLineNotificationResponse
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.domain.repositories import (
    TimesheetLineGateway,
    TimesheetLineNotificationRepository,
)
from app.users.domain.repositories import EmployeeGateway
from app.timesheet_line.application.excepctions.exceptions import (
    TimesheetListError,
    InvalidDateRangeError,
    InvalidEmployeeIdError,
    EmployeeNotExistsError,
)


class ListTimesheetLinesUseCase:
    def __init__(
        self,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_gateway: EmployeeGateway,
        notification_repository: TimesheetLineNotificationRepository,
    ) -> None:
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway
        self.notification_repository: TimesheetLineNotificationRepository = (
            notification_repository
        )

    def execute(
        self,
        employee_id: int | None,
        date_from: date | None,
        date_to: date | None,
        project_id: int | None,
        validated: bool | None,
        team: bool | None,
        uid: int,
    ) -> List[DetailedTimesheetLine]:
        # Validación de employee_id
        if employee_id is not None and employee_id <= 0:
            raise InvalidEmployeeIdError(employee_id)

        # Verificar si el empleado existe
        if employee_id is not None and not self.employee_gateway.exists_by_id(
            employee_id
        ):
            raise EmployeeNotExistsError(employee_id)

        # Validación de rango de fechas
        if date_from is not None and date_to is not None and date_from > date_to:
            raise InvalidDateRangeError(date_from.isoformat(), date_to.isoformat())

        timesheets = self.timesheet_line_gateway.all(
            employee_id, date_from, date_to, project_id, validated, team, uid
        )

        employees = self.employee_gateway.all()
        employees_dict = {employee.id: employee for employee in employees}
        # Devolver la lista de timesheets (puede estar vacía, y eso está bien)
        for timesheet in timesheets:
            # es ineficiente, pero van a ser pocos. Todo: mejorar
            notification = self.notification_repository.get_by_timesheet_id(
                timesheet.id
            )
            if notification is not None:
                timesheet.notification = TimesheetLineNotificationResponse(
                    id=notification.id,
                    sender_name=employees_dict[notification.approver_id].full_name,
                    sended_at=notification.created_at,
                )
        return timesheets
