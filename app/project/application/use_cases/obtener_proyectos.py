from app.project.domain.gateway import ProjectGateway
from app.project.domain.models import Project


class ObtenerProyectosUseCase:
    """Caso de uso para obtener los proyectos de un usuario."""

    def __init__(self, project_gateway: ProjectGateway):
        self.project_gateway = project_gateway

    def execute(self, user_id: int) -> list[Project]:
        """Ejecuta el caso de uso.

        Args:
            user_id (int): ID del usuario del cual obtener los proyectos.

        Returns:
            list[Project]: Lista de proyectos del usuario.
        """
        return self.project_gateway.all(user_id)
