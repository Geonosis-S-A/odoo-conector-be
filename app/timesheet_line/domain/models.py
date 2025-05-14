# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass

# Ejemplo. Hay que ver si le damos uso.
@dataclass
class TimesheetLine:
    user_id: int
    project_id: int
    hours: float
    date: str

    @classmethod
    def from_request(cls, user_id: int, project_id: int, hours: float, date: str):
        return cls(user_id=user_id, project_id=project_id, hours=hours, date=date)