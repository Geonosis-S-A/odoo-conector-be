from datetime import date
from typing import List, Dict, Any, cast, Optional
import xmlrpc.client

from app.dashboard.domain.repositories import DashboardDataGateway
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project  
from app.task.domain.models import TaskInfo, TaskWithParentInfo
from app.shared.infra.external.odoo.odoo_client import OdooConnection


class OdooDashboardDataGateway(DashboardDataGateway):
    """Implementación concreta del gateway de datos para dashboard usando Odoo directamente."""

    def __init__(self, odoo_client: OdooConnection):
        self.odoo_client = odoo_client

    def get_team_timesheet_data(
        self, 
        user_id: int, 
        date_from: date, 
        date_to: date,
        task_gateway
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene datos de timesheet del equipo haciendo consulta directa a Odoo.
        """
        try:
            # Construir dominio para filtrar por equipo (copiado de TimesheetLineGateway)
            domain = [
                ("is_timesheet", "=", True),
                ("date", ">=", date_from.isoformat()),
                ("date", "<=", date_to.isoformat()),
                # Filtro de equipo
                "|",
                "|", 
                ("employee_id.timesheet_manager_id", "=", user_id),
                ("employee_id.parent_id.user_id", "=", user_id),
                ("employee_id.is_subordinate", "=", True),
            ]

            # Ejecutar consulta a Odoo
            odoo_timesheet_lines = cast(
                List[Dict[str, Any]],
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "account.analytic.line",
                    "search_read",
                    [domain],
                    {
                        "fields": [
                            "name",
                            "date", 
                            "unit_amount",
                            "employee_id",
                            "project_id",
                            "task_id",
                            "create_date",
                            "validated",
                        ],
                    },
                ),
            )

            # Obtener información completa de las tareas para manejar parent_id
            task_ids = []
            for line in odoo_timesheet_lines:
                task_id_info = line.get("task_id")
                if task_id_info and isinstance(task_id_info, list) and len(task_id_info) > 0:
                    task_ids.append(task_id_info[0])
            
            task_info_map = task_gateway.get_tasks_info_with_parents(task_ids) if task_ids else {}

            # Transformar datos de Odoo a nuestro modelo de dominio
            parsed_lines = [
                self._transform_odoo_to_detailed_domain(line, task_info_map)
                for line in odoo_timesheet_lines
            ]

            return parsed_lines

        except Exception as e:
            raise Exception(f"Error al obtener datos de timesheet del equipo: {str(e)}")

    def get_active_team_users_count(self, user_id: int) -> int:
        """
        Obtiene la cantidad de usuarios activos en el equipo consultando directamente a Odoo.
        """
        try:
            # Construir dominio para obtener empleados del equipo que estén activos
            domain = [
                ("active", "=", True),     # Están activos  ---> VALIDAR ESTO
                "|",
                "|",
                ("timesheet_manager_id", "=", user_id),
                ("parent_id.user_id", "=", user_id),
                ("is_subordinate", "=", True),
            ]

            # Contar empleados que cumplen el criterio
            employee_count = cast(
                int,
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "hr.employee",
                    "search_count",
                    [domain],
                ),
            )

            return employee_count

        except Exception as e:
            raise Exception(f"Error al obtener cantidad de usuarios del equipo: {str(e)}")


    def _transform_odoo_to_detailed_domain(self, odoo_line: Dict[str, Any], task_info_map: Optional[Dict[int, TaskWithParentInfo]] = None) -> DetailedTimesheetLine:
        """
        Transforma una línea de Odoo al modelo de dominio DetailedTimesheetLine.
        """
        from datetime import datetime

        # Extraer información del proyecto
        project_info = odoo_line.get("project_id")
        if project_info and isinstance(project_info, list) and len(project_info) >= 2:
            project = Project(id=project_info[0], name=project_info[1])
        else:
            # Proyecto por defecto si no hay información
            project = Project(id=0, name="Sin proyecto")

        # Extraer información de la tarea
        task_info = odoo_line.get("task_id") 
        task = None
        if task_info and isinstance(task_info, list) and len(task_info) >= 2:
            task_id = task_info[0]
            task_name = task_info[1]
            
            # Si tenemos información completa de la tarea, usar nombre con concatenación si aplica
            if task_info_map and task_id in task_info_map:
                task_with_parent = task_info_map[task_id]
                task_name = task_with_parent.get_display_name()
            
            task = TaskInfo(
                id=task_id,
                name=task_name,
                project_id=project.id,
                project_name=project.name,
            )

        # Extraer información del empleado
        employee_info = odoo_line.get("employee_id")
        employee_id = employee_info[0] if employee_info and isinstance(employee_info, list) else 0

        # Parsear fecha de creación
        create_date = None
        if odoo_line.get("create_date"):
            try:
                create_date = datetime.fromisoformat(odoo_line["create_date"].replace("Z", "+00:00"))
            except:
                create_date = None

        # Parsear fecha
        line_date = datetime.strptime(odoo_line["date"], "%Y-%m-%d").date()

        return DetailedTimesheetLine(
            id=odoo_line["id"],
            name=odoo_line.get("name", ""),
            employee_id=employee_id,
            project=project,
            task=task,
            hours=float(odoo_line.get("unit_amount", 0)),
            date=line_date,
            validated=bool(odoo_line.get("validated", False)),
            create_date=create_date,
            notification=None,  # No necesitamos notificaciones para dashboard
        )
