from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List, Dict, Any
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
        user_id: Optional[int] = None,
        team_members_ids: Optional[list[int]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[DetailedTimesheetLine]: ...

    @abstractmethod
    def count(
        self,
        employee_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        project_id: Optional[int] = None,
        validated: Optional[bool] = None,
        team: Optional[bool] = None,
        user_id: Optional[int] = None,
        team_members_ids: Optional[list[int]] = None,
    ) -> int: ...

    @abstractmethod
    def all_by_employees(
        self, employee_ids: list[int], date_from: date, date_to: date
    ) -> list[Dict[str, Any]]: ...

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


    @abstractmethod
    def get_team_users(
        self, user_id: int, employee_id: int
    ) -> list[Dict[str, Any]]: ...

    @abstractmethod
    def get_by_task_or_project(
        self,
        task_id: Optional[int] = None,
        project_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene líneas de timesheet filtradas por tarea o proyecto en un período específico.
        
        Args:
            task_id: ID de la tarea a filtrar (opcional)
            project_id: ID del proyecto a filtrar (opcional, usado cuando task_id es None)
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período
            
        Returns:
            Lista de DetailedTimesheetLine que coinciden con los criterios
        """
        ...
    
    @abstractmethod
    def all_by_employees_with_requester_user_id(
        self, employee_ids: list[int], date_from: date, date_to: date, requester_user_id: int
    ) -> List[Dict[str, Any]]: ...


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
