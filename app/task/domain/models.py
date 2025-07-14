# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass


# Ejemplo. Hay que ver si le damos uso.
@dataclass
class Task:
    id: int
    name: str
    project_id: int
    project_name: str

    @classmethod
    def from_request(cls, id: int, name: str, project_id: int, project_name: str):
        return cls(id=id, name=name, project_id=project_id, project_name=project_name)
