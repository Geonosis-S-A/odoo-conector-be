# Es un ejemplo, podría tener otro nombre etc

from typing import List
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

    def execute(
        self, requests: list[CargarHorasRequest]
    ) -> list[DetailedTimesheetLine]:
        timesheet_lines = []
        for req in requests:
            if req.hours < 0:
                raise InvalidHoursError(req.hours)

            timesheet_line = TimesheetLine.from_request(
                id=None,
                name=req.name,
                employee_id=req.employee_id,
                project_id=req.project_id,
                hours=req.hours,
                date=req.date,
                task_id=req.task_id,
            )
            timesheet_lines.append(timesheet_line)

        # Crear todas las líneas en batch
        line_ids = self.timesheet_line_gateway.create(timesheet_lines)
        if not line_ids:
            raise TimesheetCreationError()

        # Obtener todas las líneas creadas
        new_timesheet_lines = self.timesheet_line_gateway.get_by_ids(line_ids)
        if not new_timesheet_lines:
            raise TimesheetCreationError(
                "No se pudieron obtener las líneas de timesheet creadas"
            )

        return new_timesheet_lines
