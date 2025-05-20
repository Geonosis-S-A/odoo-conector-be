# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass


# Ejemplo. Hay que ver si le damos uso.
@dataclass
class Task:
    id: int
    name: str

    @classmethod
    def from_request(cls, id: int, name: str):
        return cls(id=id, name=name)
