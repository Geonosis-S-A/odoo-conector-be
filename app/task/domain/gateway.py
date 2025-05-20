from abc import ABC, abstractmethod
from app.task.domain.models import Task

# Se definen las interfaces de los repositorios


class TaskGateway(ABC):
    @abstractmethod
    def all(self, project_id: int) -> list[Task]:
        pass
