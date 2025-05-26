from typing import Optional
from pydantic import BaseModel
from datetime import date, datetime

from app.project.api.schemas import ProjectResponse
from app.task.api.schemas import TaskResponse


class CargarHorasRequest(BaseModel):
    name: str
    employee_id: int
    project_id: int
    hours: float
    date: date
    task_id: int | None = None


class DetailedTimesheetLineResponse(BaseModel):
    id: int
    name: str
    employee_id: int
    project: ProjectResponse
    task: Optional[TaskResponse]
    hours: float
    date: date
    create_date: Optional[datetime] = None
