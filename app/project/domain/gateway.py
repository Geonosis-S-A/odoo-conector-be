from abc import ABC, abstractmethod
from app.project.domain.models import Project

# Se definen las interfaces de los repositorios


class ProjectGateway(ABC):
    @abstractmethod
    def all(self) -> list[Project]:
        pass
