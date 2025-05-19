# Es un ejemplo, podría tener otro nombre etc

from app.timesheet_line.api.schemas import CargarHorasRequest
from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineRepository


class CargarHorasUseCase():
    def __init__(self, odoo_repository: TimesheetLineRepository):
        self.odoo_repo = odoo_repository
    
    def execute(self, req: CargarHorasRequest):
        timesheet_line = TimesheetLine.from_request(name=req.name, employee_id=req.employee_id, project_id=req.project_id, hours=req.hours, date=req.date)
        self.odoo_repo.create(timesheet_line)
