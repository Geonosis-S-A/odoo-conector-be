from typing import List, Dict, Any, cast
from app.task.domain.gateway import TaskGateway
from app.task.domain.models import Task, TaskWithParentInfo
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

    def get_tasks_info_with_parents(self, task_ids: List[int]) -> Dict[int, TaskWithParentInfo]:
        """Obtiene información completa de las tareas incluyendo parent_id."""
        try:
            if not task_ids:
                return {}
            
            # Obtener información de todas las tareas
            tasks_data = cast(
                List[Dict[str, Any]],
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "project.task",
                    "read",
                    [task_ids],
                    {"fields": ["id", "name", "parent_id", "project_id"]},
                ),
            )
            
            # Crear mapa de tareas raw por ID
            raw_task_map = {task["id"]: task for task in tasks_data}
            
            # Obtener IDs de tareas padre si existen
            parent_ids = [task["parent_id"][0] for task in tasks_data 
                         if task.get("parent_id") and isinstance(task["parent_id"], list)]
            
            # Obtener información de tareas padre si las hay
            parent_info = {}
            if parent_ids:
                parent_tasks_data = cast(
                    List[Dict[str, Any]],
                    self.odoo_client["models"].execute_kw(
                        self.odoo_client["ODOO_DB"],
                        self.odoo_client["uid"],
                        self.odoo_client["ODOO_PASSWORD"],
                        "project.task",
                        "read",
                        [parent_ids],
                        {"fields": ["id", "name", "project_id"]},
                    ),
                )
                
                # Crear mapa de información de padres
                parent_info = {parent["id"]: parent for parent in parent_tasks_data}
            
            # Transformar a TaskWithParentInfo
            result = {}
            for task_id in task_ids:
                if task_id in raw_task_map:
                    task_data = raw_task_map[task_id]
                    
                    # Extraer información del proyecto
                    project_id = task_data["project_id"][0] if isinstance(task_data["project_id"], list) else task_data["project_id"]
                    project_name = task_data["project_id"][1] if isinstance(task_data["project_id"], list) and len(task_data["project_id"]) > 1 else ""
                    
                    # Extraer información del padre si existe
                    parent_id = None
                    parent_name = None
                    if task_data.get("parent_id") and isinstance(task_data["parent_id"], list):
                        parent_id = task_data["parent_id"][0]
                        if parent_id in parent_info:
                            parent_name = parent_info[parent_id]["name"]
                    
                    # Crear TaskWithParentInfo
                    result[task_id] = TaskWithParentInfo(
                        id=task_data["id"],
                        name=task_data["name"],
                        project_id=project_id,
                        project_name=project_name,
                        parent_id=parent_id,
                        parent_name=parent_name
                    )
            
            return result
            
        except Exception as e:
            return {}