from abc import ABC, abstractmethod
from app.task.domain.models import Task
from app.project.domain.models import Project

# Se definen las interfaces de los repositorios


class TaskGateway(ABC):
    @abstractmethod
    def all(self, project_id: int) -> list[Task] | None:
        pass

    @abstractmethod
    def get_project_by_id(self, project_id: int) -> Project | None:
        pass
