from app.task.domain.gateway import TaskGateway
from app.task.domain.models import Task


class ObtenerTareasUseCase:
    """Caso de uso para obtener las tareas."""

    def __init__(self, task_gateway: TaskGateway):
        self.task_gateway = task_gateway

    def execute(self, project_id: int) -> list[Task]:
        """Ejecuta el caso de uso.

        Args:
            project_id (int): ID del proyecto del cual obtener las tareas.

        Returns:
            list[Task]: Lista de tareas.
        """
        return self.task_gateway.all(project_id)
