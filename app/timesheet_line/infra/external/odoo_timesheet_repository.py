

from app.timesheet_line.domain.repositories import TimesheetLineRepository


class OdooTimesheetLineRepository(TimesheetLineRepository):
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client

    def save(self, timesheet_line) -> None:
        raise NotImplementedError("Saving timesheet lines is not implemented in Odoo repository.")

    def all(self):
        raise NotImplementedError("Fetching all timesheet lines is not implemented in Odoo repository.")