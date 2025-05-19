from abc import ABC, abstractmethod
from app.timesheet_line.domain.models import TimesheetLine

class TimesheetLineRepository(ABC):
    @abstractmethod
    def create(self, timesheet_line: TimesheetLine) -> None: ...

    @abstractmethod
    def all(self) -> list[TimesheetLine]: ...
