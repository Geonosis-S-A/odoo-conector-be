from abc import ABC, abstractmethod
from app.timesheet_line.domain.models import TimesheetLine


class TimesheetLineRepository(ABC):
    @abstractmethod
    def create(self, timesheet_line: TimesheetLine) -> int: ...

    @abstractmethod
    def all(self) -> list[TimesheetLine]: ...

    @abstractmethod
    def delete(self, timesheet_line_id: int) -> bool: ...
