# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Project:
    id: int
    name: str
    manager_user_id: Optional[int] = None

    @classmethod
    def from_request(cls, id: int, name: str):
        return cls(id=id, name=name)


@dataclass
class ProjectAssignment:
    id: int
    employee_id: int
    project_id: int
    date_start: date
    date_end: Optional[date]
    allocation_percentage: float
