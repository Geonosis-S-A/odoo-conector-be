"""Caso de uso para exportar timesheets como excel."""

from datetime import date
from typing import Dict, List
from app.auth.application.use_cases.exceptions.exceptions import UserNotFound
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway
from app.task.domain.gateway import TaskGateway
from app.task.domain.models import TaskWithParentInfo
import pandas as pd


class ExportTimesheetsByTeamUseCase:
    """Caso de uso para exportar timesheets como excel por equipo."""

    def __init__(
        self,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_gateway: EmployeeGateway,
        task_gateway: TaskGateway,
        manager_employee_id: int,
    ):
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway
        self.task_gateway = task_gateway
        self.manager_employee_id = manager_employee_id

    def _build_task_hierarchy(
        self, task_info: TaskWithParentInfo, tasks_info: Dict[int, TaskWithParentInfo]
    ) -> List[str]:
        """Construye la jerarquía completa de una tarea desde la raíz hasta la tarea actual."""
        current_task = task_info

        # Construir la cadena de jerarquía de abajo hacia arriba
        chain = []
        while current_task:
            chain.append(current_task.name)
            if current_task.parent_id and current_task.parent_id in tasks_info:
                current_task = tasks_info[current_task.parent_id]
            else:
                current_task = None

        # Invertir para obtener de arriba hacia abajo (padre -> hijo -> nieto)
        return list(reversed(chain))

    def _get_max_hierarchy_depth(
        self, tasks_info: Dict[int, TaskWithParentInfo]
    ) -> int:
        """Calcula la profundidad máxima de jerarquía en todas las tareas."""
        max_depth = 0
        for task_info in tasks_info.values():
            hierarchy = self._build_task_hierarchy(task_info, tasks_info)
            max_depth = max(max_depth, len(hierarchy))
        return max_depth

    def execute(self, date_from: date, date_to: date):
        manager_user_id = self.employee_gateway.get_user_id_by_employee_id(
            self.manager_employee_id
        )
        if not manager_user_id:
            raise UserNotFound("Manager not found")
        users = self.timesheet_line_gateway.get_team_users(
            manager_user_id, self.manager_employee_id
        )
        team_employee_ids = [user["id"] for user in users]

        # Obtengo los timesheets de los ids que paso y que pertenecen al equipo del manager
        timesheet_lines = (
            self.timesheet_line_gateway.all_by_employees_with_requester_user_id(
                team_employee_ids, date_from, date_to, manager_user_id
            )
        )

        # Extraer todos los task_ids únicos de los timesheets
        task_ids = set()
        for line in timesheet_lines:
            if (
                line.get("task_id")
                and isinstance(line["task_id"], list)
                and len(line["task_id"]) > 0
            ):
                task_ids.add(line["task_id"][0])

        # Obtener información completa de las tareas incluyendo jerarquías
        tasks_info = {}
        if task_ids:
            tasks_info = self.task_gateway.get_tasks_info_with_parents(list(task_ids))

            # Obtener todas las tareas padre que necesitamos para construir jerarquías completas
            all_parent_ids = set()
            for task_info in tasks_info.values():
                current_task = task_info
                while current_task and current_task.parent_id:
                    all_parent_ids.add(current_task.parent_id)
                    # Para evitar bucles infinitos, solo seguimos si no tenemos ya la info del padre
                    if current_task.parent_id not in tasks_info:
                        break
                    current_task = tasks_info.get(current_task.parent_id)

            # Obtener información de tareas padre faltantes
            missing_parent_ids = all_parent_ids - set(tasks_info.keys())
            if missing_parent_ids:
                parent_tasks_info = self.task_gateway.get_tasks_info_with_parents(
                    list(missing_parent_ids)
                )
                tasks_info.update(parent_tasks_info)

        df = pd.DataFrame(timesheet_lines)

        df["empleado"] = df["employee_id"].apply(lambda x: x[1])
        df["proyecto"] = df["project_id"].apply(lambda x: x[1])

        # Calcular la profundidad máxima de jerarquía para crear las columnas necesarias
        max_depth = self._get_max_hierarchy_depth(tasks_info) if tasks_info else 1

        # Crear funciones para extraer cada nivel de la jerarquía
        def get_task_hierarchy_level(task_id_field, level_index):
            if not isinstance(task_id_field, list) or len(task_id_field) == 0:
                return "-"

            task_id = task_id_field[0]
            if task_id not in tasks_info:
                # Si no tenemos info de la tarea, usar el nombre original como último nivel
                if level_index == 0:
                    return task_id_field[1] if len(task_id_field) > 1 else "-"
                return "-"

            hierarchy = self._build_task_hierarchy(tasks_info[task_id], tasks_info)
            if level_index < len(hierarchy):
                return hierarchy[level_index]
            return "-"

        # Agregar columnas dinámicas para cada nivel de jerarquía
        for i in range(max_depth):
            if i == 0:
                column_name = "tarea"
            else:
                column_name = f"subtarea_{i}"

            df[column_name] = df["task_id"].apply(
                lambda x: get_task_hierarchy_level(x, i)
            )

        # Si no hay jerarquía, mantener la columna tarea básica
        if max_depth == 0:
            df["tarea"] = df["task_id"].apply(
                lambda x: x[1] if isinstance(x, list) else "-"
            )

        df["name"] = df["name"].apply(lambda x: "-" if x == "/" else x)

        df = df.drop(columns=["employee_id", "project_id", "task_id"])
        df = df.rename(
            columns={
                "id": "id_carga",
                "date": "fecha",
                "unit_amount": "cantidad",
                "name": "descripcion",
                "create_date": "fecha de carga",
            }
        )
        return df
