from abc import ABC, abstractmethod
from app.timesheet_line.domain.models import TimesheetLine


class TimesheetLineGateway(ABC):
    @abstractmethod
    def create(self, timesheet_line: TimesheetLine) -> int: ...

    @abstractmethod
    def all(self, employee_id: int | None = None) -> list[TimesheetLine]: ...

    @abstractmethod
    def delete(self, timesheet_line_id: int) -> bool: ...
