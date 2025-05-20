from pydantic import BaseModel


class ProjectResponse(BaseModel):
    id: int
    name: str
