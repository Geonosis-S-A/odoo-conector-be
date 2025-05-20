from app.task.domain.gateway import TaskGateway
from app.task.domain.models import Task


class OdooTaskGateway(TaskGateway):
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client

    def all(self, project_id: int) -> list[Task]:
        domain = [("project_id", "=", project_id)]

        tasks = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.task",
            "search_read",
            [domain],
            {"fields": ["id", "name"]},
        )

        return [Task(id=task["id"], name=task["name"]) for task in tasks]
