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
