from pydantic import BaseModel
from datetime import date


class CargarHorasRequest(BaseModel):
    name: str
    employee_id: int
    project_id: int
    hours: float
    date: date
