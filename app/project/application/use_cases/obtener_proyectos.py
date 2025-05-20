from app.project.domain.gateway import ProjectGateway
from app.project.domain.models import Project


class ObtenerProyectosUseCase:
    """Caso de uso para obtener los proyectos."""

    def __init__(self, project_gateway: ProjectGateway):
        self.project_gateway = project_gateway

    def execute(self, user_id: int | None = None) -> list[Project]:
        """Ejecuta el caso de uso.

        Args:
            user_id (int | None, optional): ID del usuario del cual obtener los proyectos.
                Si es None, devuelve todos los proyectos.

        Returns:
            list[Project]: Lista de proyectos.
        """
        return self.project_gateway.all(user_id)
