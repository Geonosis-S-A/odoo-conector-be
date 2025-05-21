from abc import ABC, abstractmethod
from app.timesheet_line.domain.models import DetailedTimesheetLine, TimesheetLine


class TimesheetLineGateway(ABC):
    @abstractmethod
    def create(self, timesheet_line: TimesheetLine) -> int: ...

    @abstractmethod
    def all(self, employee_id: int | None = None) -> list[DetailedTimesheetLine]: ...

    @abstractmethod
    def delete(self, timesheet_line_id: int) -> bool: ...

    @abstractmethod
    def get_by_id(self, timesheet_line_id: int) -> DetailedTimesheetLine: ...
