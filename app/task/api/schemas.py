from typing import List
from app.task.domain.models import Task
from pydantic import BaseModel


class TaskInfoResponse(BaseModel):
    id: int
    name: str
    project_id: int
    project_name: str


class TaskResponse(TaskInfoResponse):
    state: str
    subtask: List["TaskResponse"]
