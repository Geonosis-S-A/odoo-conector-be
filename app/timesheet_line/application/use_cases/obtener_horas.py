from typing import List
from datetime import date

from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway
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
    ) -> None:
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway

    def execute(
        self,
        employee_id: int,
        date_from: date,
        date_to: date,
    ) -> List[DetailedTimesheetLine]:
        # Validación de employee_id
        if employee_id <= 0:
            raise InvalidEmployeeIdError(employee_id)

        # Verificar si el empleado existe
        if not self.employee_gateway.exists_by_id(employee_id):
            raise EmployeeNotExistsError(employee_id)

        # Validación de rango de fechas
        if date_from > date_to:
            raise InvalidDateRangeError(date_from.isoformat(), date_to.isoformat())

        try:
            return self.timesheet_line_gateway.all(employee_id, date_from, date_to)
        except Exception as e:
            raise TimesheetListError(str(e))
