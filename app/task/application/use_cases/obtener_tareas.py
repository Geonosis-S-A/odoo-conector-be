from app.task.domain.gateway import TaskGateway
from app.task.domain.models import Task
from app.task.application.Exeptions import (
    ProjectNotFound,
    TasksNotFound_userId,
)
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.auth.application.use_cases.exceptions.exceptions import (
    UserNotFound,
)


class ObtenerTareasUseCase:
    """Caso de uso para obtener las tareas."""

    def __init__(
        self,
        task_gateway: TaskGateway,
        odoo_task_gateway: OdooTaskGateway,
        odoo_employee_gateway: OdooEmployeeGateway,
    ):
        self.task_gateway = task_gateway
        self.odoo_task_gateway = odoo_task_gateway
        self.odoo_employee_gateway = odoo_employee_gateway

    def execute(self, project_id: int) -> list[Task]:
        """Ejecuta el caso de uso.

        Args:
            project_id (int): ID del proyecto del cual obtener las tareas.

        Returns:
            list[Task]: Lista de tareas.
        """
        project = self.odoo_task_gateway.get_project_by_id(project_id)
        if not project:
            raise ProjectNotFound(project_id)

        tasks = self.task_gateway.all(project_id)
        if tasks is None:
            return []
        return tasks

    def execute_by_user(self, user_id: int) -> list[Task]:
        """Ejecuta el caso de uso para obtener tareas por usuario.

        Args:
            user_id (int): ID del usuario del cual obtener las tareas.

        Returns:
            list[Task]: Lista de tareas asignadas al usuario.
        """
        # TODO molo: Validar que el usuario exista en Odoo (cuando feli implemente el get_user_by_id en el user gateway)

        user = self.odoo_employee_gateway.exists_by_id(user_id)
        if not user:
            raise UserNotFound(f"El usuario {user_id} no existe en Odoo")

        tasks = self.task_gateway.all_by_user(user_id)
        if not tasks:
            raise TasksNotFound_userId(user_id)
        return tasks
