from app.project.domain.gateway import ProjectGateway
from app.project.domain.models import Project
from app.project.infra.external.odd_project_gateway import OdooProjectGateway
from app.task.application.Exeptions import ProjectsNotFound


class ObtenerProyectosUseCase:
    """Caso de uso para obtener los proyectos."""

    def __init__(self, project_gateway: ProjectGateway):
        self.project_gateway = project_gateway

    def execute(self) -> list[Project]:
        """Ejecuta el caso de uso.

        Args:
            user_id (int | None, optional): ID del usuario del cual obtener los proyectos.
                Si es None, devuelve todos los proyectos.

        Returns:
            list[Project]: Lista de proyectos.
        """
        projects = self.project_gateway.all()

        # Si no hay proyectos, retornamos una lista vacía
        if not projects:
            return []

        # Extraer proyectos únicos de las tareas
        projects_dict = {}
        for project in projects:
            if project.id not in projects_dict:
                projects_dict[project.id] = Project(id=project.id, name=project.name)

        return list(projects_dict.values())
