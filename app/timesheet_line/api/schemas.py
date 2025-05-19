from pydantic import BaseModel


class CargarHorasRequest(BaseModel):
    name: str
    employee_id: int
    project_id: int
    hours: float
    date: str