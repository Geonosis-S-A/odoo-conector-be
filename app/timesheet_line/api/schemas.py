from typing import Optional, List
from pydantic import BaseModel
from datetime import date, datetime

from app.project.api.schemas import ProjectResponse
from app.task.api.schemas import TaskInfoResponse


class CargarHorasRequest(BaseModel):
    name: Optional[str] | None = None
    employee_id: int
    project_id: int
    hours: float
    date: date
    task_id: int | None = None


class TimesheetLineNotificationResponse(BaseModel):
    id: int
    sender_name: str
    sended_at: datetime


class DetailedTimesheetLineResponse(BaseModel):
    id: int
    name: str
    employee_id: int
    project: ProjectResponse
    task: Optional[TaskInfoResponse]
    hours: float
    date: date
    create_date: Optional[datetime] = None
    validated: bool
    notification: Optional[TimesheetLineNotificationResponse] = None


class EditTimesheetRequest(BaseModel):
    id: int
    name: str
    employee_id: int
    project_id: int
    hours: float
    date: date
    task_id: Optional[int] = None
    validated: bool


class DeleteTimesheetRequest(BaseModel):
    ids: List[int]


class ValidateTimesheetRequest(BaseModel):
    timesheetline_ids: List[int]
