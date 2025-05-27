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

    def execute_by_user(self, user_id: int) -> list[Task]:
        """Ejecuta el caso de uso para obtener tareas por usuario.

        Args:
            user_id (int): ID del usuario del cual obtener las tareas.

        Returns:
            list[Task]: Lista de tareas asignadas al usuario.
        """
        return self.task_gateway.all_by_user(user_id)
