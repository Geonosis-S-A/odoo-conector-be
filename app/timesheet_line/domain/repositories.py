from abc import ABC, abstractmethod
from app.timesheet_line.domain.models import TimesheetLine

# Se definen las interfaces de los repositorios

class TimesheetLineRepository(ABC):
    @abstractmethod
    def save(self, timesheet_line: TimesheetLine) -> None:
        pass

    @abstractmethod
    def all(self) -> list[TimesheetLine]:
        pass
