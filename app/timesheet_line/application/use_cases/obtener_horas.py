from typing import List, Optional

from app.timesheet_line.domain.models import TimesheetLine


class ListTimesheetLinesUseCase:
    def __init__(self, gateway):
        self.gateway = gateway

    def execute(self, employee_id: Optional[int] = None) -> List[TimesheetLine]:
        return self.gateway.all(employee_id)
