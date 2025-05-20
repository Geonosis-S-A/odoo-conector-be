# Es un ejemplo, podría tener otro nombre etc

from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineGateway


class CargarHorasUseCase:
    def __init__(self, odoo_gateway: TimesheetLineGateway):
        self.odoo_gateway = odoo_gateway

    def execute(self, req: CargarHorasRequest):
        # Validación de horas negativas
        if req.hours < 0:
            raise ValueError("Las horas no pueden ser negativas")

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
        return self.odoo_gateway.create(timesheet_line)
