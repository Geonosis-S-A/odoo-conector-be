from typing import List, Optional
from datetime import date

from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)


class ListTimesheetLinesUseCase:
    def __init__(self, gateway: OdooTimesheetLineGateway) -> None:
        self.gateway = gateway

    def execute(
        self,
        employee_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[DetailedTimesheetLine]:
        return self.gateway.all(employee_id, date_from, date_to)
