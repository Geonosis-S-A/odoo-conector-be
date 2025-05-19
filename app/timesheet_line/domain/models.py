# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass

# Ejemplo. Hay que ver si le damos uso.
@dataclass
class TimesheetLine:
    name: str
    employee_id: int
    project_id: int
    hours: float
    date: str

    @classmethod
    def from_request(cls, employee_id: int, project_id: int, hours: float, date: str, name: str):
        return cls(employee_id=employee_id, project_id=project_id, hours=hours, date=date, name=name)