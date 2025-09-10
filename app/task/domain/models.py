# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass
from typing import Optional



@dataclass
class Task:
    id: int
    name: str
    project_id: int
    project_name: str
    state: str
    subtask: list["Task"]


@dataclass
class TaskInfo:
    id: int
    name: str
    project_id: int
    project_name: str

    @classmethod
    def from_request(
        cls,
        id: int,
        name: str,
        project_id: int,
        project_name: str,
    ):
        return cls(
            id=id,
            name=name,
            project_id=project_id,
            project_name=project_name,
        )


@dataclass
class TaskWithParentInfo:
    """Información completa de una tarea incluyendo datos del padre si existe."""
    id: int
    name: str
    project_id: int
    project_name: str
    parent_id: Optional[int] = None
    parent_name: Optional[str] = None
    
    def get_display_name(self) -> str:
        """
        Retorna el nombre para mostrar, concatenando padre -> hijo si tiene padre.
        
        Returns:
            str: "nombre_padre -> nombre_hijo" si tiene padre, solo "nombre" si no.
        """
        if self.parent_name:
            return f"{self.parent_name} -> {self.name}"
        return self.name
