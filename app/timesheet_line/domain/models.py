# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass
from datetime import date as date_t, datetime
from typing import Optional

from app.project.domain.models import Project
from app.task.domain.models import Task


# Ejemplo. Hay que ver si le damos uso.
@dataclass
class TimesheetLine:
    id: int | None
    name: str | None
    employee_id: int
    project_id: int
    hours: float
    date: date_t
    task_id: Optional[int] = None

    @classmethod
    def from_request(
        cls,
        id: int | None,
        name: str | None,
        employee_id: int,
        project_id: int,
        hours: float,
        date: date_t,
        task_id: int | None = None,
    ):
        return cls(
            id=id,
            name=name,
            employee_id=employee_id,
            project_id=project_id,
            hours=hours,
            date=date,
            task_id=task_id,
        )


@dataclass
class DetailedTimesheetLine:
    id: int
    name: str
    employee_id: int
    project: Project
    task: Task | None
    hours: float
    date: date_t
    validated: bool
    create_date: Optional[datetime] = None
