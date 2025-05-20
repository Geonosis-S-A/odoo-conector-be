# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass
from datetime import date as date_t


# Ejemplo. Hay que ver si le damos uso.
@dataclass
class TimesheetLine:
    id: int | None
    name: str
    employee_id: int
    project_id: int
    hours: float
    date: date_t
    task_id: int | None = None

    @classmethod
    def from_request(
        cls,
        id: int | None,
        name: str,
        employee_id: int,
        project_id: int,
        hours: float,
        date: date_t,
        task_id: int | None = None,
    ):
        return cls(
            id=id,
            employee_id=employee_id,
            project_id=project_id,
            hours=hours,
            date=date,
            name=name,
            task_id=task_id,
        )
