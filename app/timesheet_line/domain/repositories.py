from abc import ABC, abstractmethod
from datetime import date
from typing import Optional
from app.timesheet_line.domain.models import DetailedTimesheetLine, TimesheetLine


class TimesheetLineGateway(ABC):
    @abstractmethod
    def create(self, timesheet_line: TimesheetLine) -> int | None: ...

    @abstractmethod
    def all(
        self,
        employee_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[DetailedTimesheetLine]: ...

    @abstractmethod
    def delete(self, timesheet_line_id: int) -> bool: ...

    @abstractmethod
    def update(self, timesheet_line: TimesheetLine) -> bool: ...

    @abstractmethod
    def get_by_id(self, timesheet_line_id: int) -> DetailedTimesheetLine | None: ...
