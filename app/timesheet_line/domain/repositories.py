from abc import ABC, abstractmethod
from datetime import date
from typing import Optional
from app.timesheet_line.domain.models import (
    CreateTimesheetLineNotification,
    DetailedTimesheetLine,
    TimesheetLine,
    TimesheetLineNotification,
)


class TimesheetLineGateway(ABC):
    @abstractmethod
    def create(self, timesheet_lines: list[TimesheetLine]) -> list[int] | None: ...

    @abstractmethod
    def all(
        self,
        employee_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        project_id: Optional[int] = None,
        validated: Optional[bool] = None,
        team: Optional[bool] = None,
        uid: Optional[int] = False,
    ) -> list[DetailedTimesheetLine]: ...

    @abstractmethod
    def delete(self, timesheet_lines_ids: list[int]) -> bool: ...

    @abstractmethod
    def update(self, timesheet_line: TimesheetLine) -> bool: ...

    @abstractmethod
    def get_by_id(self, timesheet_line_id: int) -> DetailedTimesheetLine | None: ...

    @abstractmethod
    def get_by_ids(
        self, timesheet_line_ids: list[int]
    ) -> list[DetailedTimesheetLine]: ...

    @abstractmethod
    def validate(self, timesheet_line_ids: list[int]) -> bool: ...


class TimesheetLineNotificationRepository(ABC):
    @abstractmethod
    def create(
        self, timesheet_line_notification: CreateTimesheetLineNotification
    ) -> bool: ...

    @abstractmethod
    def delete(self, timesheet_line_notification_id: int) -> bool: ...

    @abstractmethod
    def get_by_timesheet_id(
        self, timesheet_line_id: int
    ) -> TimesheetLineNotification | None: ...

    @abstractmethod
    def get_by_timesheet_ids(
        self, timesheet_line_ids: list[int]
    ) -> list[TimesheetLineNotification]: ...
