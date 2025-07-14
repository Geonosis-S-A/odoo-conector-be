from app.task.domain.gateway import TaskGateway
from app.task.domain.models import Task
from app.project.domain.models import Project


class OdooTaskGateway(TaskGateway):
    def __init__(self, odoo_client):
        self.odoo_client = odoo_client

    def all(self, project_id: int) -> list[Task] | None:
        domain = [("project_id", "=", project_id)]

        tasks = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.task",
            "search_read",
            [domain],
            {"fields": ["id", "name", "project_id"]},
        )

        if not tasks:
            return None

        return [
            Task(
                id=task["id"],
                name=task["name"],
                project_id=task["project_id"][0],
                project_name=task["project_id"][1],
            )
            for task in tasks
        ]

    def all_by_user(self, user_id: int) -> list[Task] | None:
        # En Odoo 16+ user_ids es Many2many, en versiones anteriores era user_id Many2one
        # Usamos user_ids para compatibilidad con versiones recientes
        domain = [("user_ids", "in", [user_id])]

        tasks = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.task",
            "search_read",
            [domain],
            {"fields": ["id", "name", "project_id"]},
        )

        if not tasks:
            return None

        return [
            Task(
                id=task["id"],
                name=task["name"],
                project_id=task["project_id"][0],
                project_name=task["project_id"][1],
            )
            for task in tasks
        ]

    def get_project_by_id(self, project_id: int) -> Project | None:
        domain = [("id", "=", project_id)]

        project = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.project",
            "search_read",
            [domain],
            {"fields": ["id", "name"]},
        )

        if not project:
            return None

        return Project(id=project[0]["id"], name=project[0]["name"])
