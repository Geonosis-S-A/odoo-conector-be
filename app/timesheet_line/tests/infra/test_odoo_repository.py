from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.infra.external.odoo.get_odoo import get_odoo_connection
from app.timesheet_line.infra.external.odoo.odoo_timesheet_repository import OdooTimesheetLineRepository


class TestOdooRepository:
    def test_returns_all_timesheet_lines_is_more_than_one(self):
        odoo_client = get_odoo_connection()
        repository = OdooTimesheetLineRepository(odoo_client)
        lines = repository.all()
        assert len(lines) > 0


    def test_create_timesheet_line_(self):
        odoo_client = get_odoo_connection()
        repository = OdooTimesheetLineRepository(odoo_client)
        prev_lines = repository.all()
        
        timesheet_line = TimesheetLine(
            employee_id=1,
            project_id=1,
            hours=1,
            date="2021-01-01",
            name="Test Timesheet Line"
        )
        repository.create(timesheet_line)
        post_lines = repository.all()
        
        assert len(post_lines) == len(prev_lines) + 1

        
