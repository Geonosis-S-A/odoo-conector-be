from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: int
    name: str
    project_id: int
    project_name: str
