from app.project.domain.gateway import ProjectGateway
from app.project.domain.models import Project
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.task.application.Exeptions import ProjectsNotFound_userId

class ObtenerProyectosUseCase:
    """Caso de uso para obtener los proyectos."""

    def __init__(self, project_gateway: ProjectGateway, task_gateway: OdooTaskGateway):
        self.project_gateway = project_gateway
        self.task_gateway = task_gateway

    def execute(self, user_id: int) -> list[Project]:
        """Ejecuta el caso de uso.

        Args:
            user_id (int | None, optional): ID del usuario del cual obtener los proyectos.
                Si es None, devuelve todos los proyectos.

        Returns:
            list[Project]: Lista de proyectos.
        """
        tasks = self.task_gateway.all_by_user(user_id)
        
        # Si no hay tareas, retornamos una lista vacía
        if not tasks:
            raise ProjectsNotFound_userId(user_id)
        
        # Extraer proyectos únicos de las tareas
        projects_dict = {}
        for task in tasks:
            if task.project_id not in projects_dict:
                projects_dict[task.project_id] = Project(
                    id=task.project_id,
                    name=task.project_name
                )
        
        return list(projects_dict.values())
