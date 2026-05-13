"""Caso de uso para exportar timesheets como excel.

VT-17 (pentest 2026-04): el export debe limitarse al mismo alcance jerárquico
que otros endpoints sensible (solo empleados en ``scoped_employee_ids``). No debe
usar la rama Odoo "(horas en proyectos que gestiono)" porque incorpora personas
fuera del equipo y junto con tarifas supone filtración masiva ARS/USD.
"""

from datetime import date
from typing import Dict, List, Optional
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.task.domain.gateway import TaskGateway
from app.task.domain.models import TaskWithParentInfo
from app.employee_price.domain.repositories import EmployeePriceRepository
from app.dashboard.application.price_utils import build_price_index, get_cost_for_date
import pandas as pd


class ExportTimesheetsByTeamUseCase:
    """Caso de uso para exportar timesheets como excel por equipo."""

    def __init__(
        self,
        timesheet_line_gateway: TimesheetLineGateway,
        task_gateway: TaskGateway,
        scoped_employee_ids: list[int],
        employee_price_repository: Optional[EmployeePriceRepository] = None,
        dolar_value: float = 0,
    ):
        self.timesheet_line_gateway = timesheet_line_gateway
        self.task_gateway = task_gateway
        self.scoped_employee_ids = scoped_employee_ids
        self.employee_price_repository = employee_price_repository
        self.dolar_value = dolar_value

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
        if not self.scoped_employee_ids:
            timesheet_lines: list = []
        else:
            timesheet_lines = self.timesheet_line_gateway.all_by_employees(
                self.scoped_employee_ids, date_from, date_to
            )

        # Obtener precios de empleados si el repositorio está disponible
        price_index = {}
        if self.employee_price_repository:
            # Extraer employee_ids únicos de los timesheets
            unique_employee_ids = set()
            for line in timesheet_lines:
                if "employee_id" in line and isinstance(line["employee_id"], list):
                    unique_employee_ids.add(line["employee_id"][0])

            # Obtener precios para estos empleados
            if unique_employee_ids:
                employee_prices = self.employee_price_repository.get_by_user_ids(
                    list(unique_employee_ids)
                )
                price_index = build_price_index(employee_prices)

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

        if not timesheet_lines:
            return pd.DataFrame(
                columns=[
                    "empleado",
                    "proyecto",
                    "tarea",
                    "fecha",
                    "mes",
                    "año",
                    "cantidad",
                    "costo_por_hora",
                    "costo_por_hora_en_dolares",
                    "descripcion",
                    "fecha de carga",
                ]
            )

        df = pd.DataFrame(timesheet_lines)

        df["empleado"] = df["employee_id"].apply(lambda x: x[1])
        df["proyecto"] = df["project_id"].apply(lambda x: x[1])

        # Agregar columna de costo por hora si hay datos de precios disponibles
        if price_index:

            def get_cost_per_hour_for_row(row):
                employee_id = (
                    row["employee_id"][0]
                    if isinstance(row["employee_id"], list)
                    else row["employee_id"]
                )
                check_date = pd.to_datetime(row["date"]).date()
                return get_cost_for_date(employee_id, check_date, price_index)

            df["costo_por_hora"] = df.apply(get_cost_per_hour_for_row, axis=1)
        else:
            df["costo_por_hora"] = 0

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

        # Extraer mes y año de la fecha
        df["mes"] = df["date"].apply(lambda x: pd.to_datetime(x).month)
        df["año"] = df["date"].apply(lambda x: pd.to_datetime(x).year)

        df = df.drop(
            columns=[c for c in ("employee_id", "project_id", "task_id", "id") if c in df.columns]
        )
        df = df.rename(
            columns={
                "date": "fecha",
                "unit_amount": "cantidad",
                "name": "descripcion",
                "create_date": "fecha de carga",
            }
        )

        # Construir lista de columnas base
        base_columns = (
            ["empleado", "proyecto", "tarea"]
            + [f"subtarea_{i + 1}" for i in range(max_depth - 1)]
            + ["fecha", "mes", "año", "cantidad"]
        )

        # Agregar columna de costo por hora si existe

        base_columns.append("costo_por_hora")

        base_columns.append("costo_por_hora_en_dolares")

        if self.dolar_value > 0:
            df["costo_por_hora_en_dolares"] = df["costo_por_hora"] / self.dolar_value
        else:
            df["costo_por_hora_en_dolares"] = 0

        # Agregar columnas finales
        base_columns.extend(["descripcion", "fecha de carga"])

        reorder_columns = base_columns
        df = df.sort_values(by="empleado")
        df = df.sort_values(by="fecha")
        return df[reorder_columns]
