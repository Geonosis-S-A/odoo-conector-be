from app.timesheet_line.domain.repositories import TimesheetLineGateway


class DeleteTimesheetUseCase:
    def __init__(self, odoo_gateway: TimesheetLineGateway):
        self.odoo_gateway = odoo_gateway

    def execute(self, timesheet_id: int) -> bool:
        return self.odoo_gateway.delete(timesheet_id)
