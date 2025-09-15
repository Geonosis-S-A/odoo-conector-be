from abc import ABC, abstractmethod
from typing import List, Dict
from app.task.domain.models import Task, TaskWithParentInfo
from app.project.domain.models import Project

# Se definen las interfaces de los repositorios


class TaskGateway(ABC):
    @abstractmethod
    def all(self, project_id: int) -> list[Task] | None:
        pass

    @abstractmethod
    def get_project_by_id(self, project_id: int) -> Project | None:
        pass

    @abstractmethod
    def get_tasks_info_with_parents(self, task_ids: List[int]) -> Dict[int, TaskWithParentInfo]:
        """
        Obtiene información completa de las tareas incluyendo parent_id.
        
        Args:
            task_ids: Lista de IDs de tareas a consultar
            
        Returns:
            Dict[int, TaskWithParentInfo]: Diccionario con task_id como clave y 
            TaskWithParentInfo como valor, incluyendo información del padre si existe.
        """
        pass
