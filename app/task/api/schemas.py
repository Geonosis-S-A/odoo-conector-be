from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: int
    name: str
