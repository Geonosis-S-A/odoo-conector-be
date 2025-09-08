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
            {"fields": ["id", "name", "project_id", "state", "child_ids", "parent_id"]},
        )

        if not tasks:
            return None

        main_tasks = []
        for task in tasks:
            if not task["parent_id"]:
                main_tasks.append(task)

        tasks_by_id = {task["id"]: task for task in tasks}

        def get_task_with_subtasks(task):
            return Task(
                id=task["id"],
                name=task["name"],
                state=task["state"],
                project_id=task["project_id"][0],
                project_name=task["project_id"][1],
                subtask=[
                    get_task_with_subtasks(tasks_by_id[sub_id])
                    for sub_id in task["child_ids"]
                ],
            )

        tasks = [get_task_with_subtasks(task) for task in main_tasks]
        return tasks

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
