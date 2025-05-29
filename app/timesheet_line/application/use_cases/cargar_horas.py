# Es un ejemplo, podría tener otro nombre etc

from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.domain.models import DetailedTimesheetLine, TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.timesheet_line.application.excepctions.exceptions import (
    InvalidHoursError,
    TimesheetCreationError,
    TimesheetNotFoundError,
)


class CargarHorasUseCase:
    def __init__(self, timesheet_line_gateway: TimesheetLineGateway):
        self.timesheet_line_gateway = timesheet_line_gateway

    def execute(self, req: CargarHorasRequest) -> DetailedTimesheetLine:
        # Validación de horas negativas
        if req.hours < 0:
            raise InvalidHoursError(req.hours)

        # Todo validar existencia de empleado y project_id
        timesheet_line = TimesheetLine.from_request(
            id=None,
            name=req.name,
            employee_id=req.employee_id,
            project_id=req.project_id,
            hours=req.hours,
            date=req.date,
            task_id=req.task_id,
        )

        line_id = self.timesheet_line_gateway.create(timesheet_line)
        if not line_id:
            raise TimesheetCreationError()

        new_timesheet_line = self.timesheet_line_gateway.get_by_id(line_id)
        if not new_timesheet_line:
            raise TimesheetNotFoundError(line_id)

        return new_timesheet_line
