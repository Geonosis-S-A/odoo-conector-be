from typing import List, Dict, Any, cast
from datetime import datetime, date
from app.timesheet_line.domain.models import DetailedTimesheetLine, TimesheetLine
from app.task.domain.models import Task
from app.project.domain.models import Project
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.shared.infra.external.odoo.odoo_client import OdooConnection


class OdooTimesheetLineGateway(TimesheetLineGateway):
    def __init__(self, odoo_client: OdooConnection) -> None:
        self.odoo_client = odoo_client

    def _transform_odoo_to_domain(self, odoo_data: Dict[str, Any]) -> TimesheetLine:
        """Transforma los datos de Odoo al modelo de dominio."""
        # Odoo devuelve la fecha como string, por ejemplo "2024-05-19"
        date_str = odoo_data.get("date")
        if not date_str:
            raise ValueError("La fecha es obligatoria para la línea de hoja de tiempo")

        date_obj: date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Odoo devuelve los IDs como tuplas [id, nombre]
        task_id: int | None = None
        raw_task_id = odoo_data.get("task_id")
        if isinstance(raw_task_id, list) and len(raw_task_id) > 0:
            task_id = raw_task_id[0]
        elif isinstance(raw_task_id, (int, str)):
            task_id = int(raw_task_id)

        return TimesheetLine(
            id=odoo_data.get("id", None),
            name=odoo_data.get("name", ""),
            employee_id=odoo_data.get("employee_id", [0, ""])[0],
            project_id=odoo_data.get("project_id", [0, ""])[0],
            hours=float(odoo_data.get("unit_amount", 0.0)),
            date=date_obj,
            task_id=task_id,
        )

    def _transform_odoo_to_detailed_domain(
        self, odoo_data: Dict[str, Any]
    ) -> DetailedTimesheetLine:
        """Transforma los datos de Odoo al modelo de dominio."""
        # Odoo devuelve la fecha como string, por ejemplo "2024-05-19"
        date_str = odoo_data.get("date")
        if not date_str:
            raise ValueError("La fecha es obligatoria para la línea de hoja de tiempo")

        date_obj: date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Odoo devuelve los IDs como tuplas [id, nombre]
        task: Task | None = None
        raw_task_id = odoo_data.get("task_id")
        if raw_task_id is None:
            task = None
        elif isinstance(raw_task_id, list) and len(raw_task_id) > 0:
            task = Task(id=raw_task_id[0], name=raw_task_id[1])

        return DetailedTimesheetLine(
            id=odoo_data.get("id", None),
            name=odoo_data.get("name", ""),
            employee_id=odoo_data.get("employee_id", [0, ""])[0],
            project=Project(
                id=odoo_data.get("project_id", [0, ""])[0],
                name=odoo_data.get("project_id", [0, ""])[1],
            ),
            hours=float(odoo_data.get("unit_amount", 0.0)),
            date=date_obj,
            task=task,
            create_date=odoo_data.get("create_date", None),
        )

    def create(self, timesheet_line: TimesheetLine) -> int:
        """Crea una nueva línea de hoja de tiempo en Odoo.

        Args:
            timesheet_line: La línea de hoja de tiempo a crear
        """
        odoo_data = {
            "name": timesheet_line.name,
            "date": timesheet_line.date.isoformat(),
            "unit_amount": timesheet_line.hours,
            "employee_id": timesheet_line.employee_id,
            "project_id": timesheet_line.project_id,
        }

        # Solo agregamos task_id si no es None
        if timesheet_line.task_id is not None:
            odoo_data["task_id"] = timesheet_line.task_id


        odoo_timesheet: int = cast(
            int,
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",  # Modelo de las líneas de hojas de tiempo
                "create",  # Método para crear un nuevo registro
                [odoo_data],
            ),
        )
        return odoo_timesheet

    def all(self, employee_id: int | None = None) -> List[DetailedTimesheetLine]:
        """Obtiene todas las líneas de hoja de tiempo de Odoo.

        Returns:
            List[TimesheetLine]: Lista de líneas de hoja de tiempo transformadas
        """
        domain = []
        if employee_id is not None:
            domain = [("employee_id", "=", employee_id)]
        odoo_timesheet_lines = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",  # Modelo de las líneas de hojas de tiempo
                "search_read",  # Método para buscar y leer registros
                [domain],  # Sin filtros (obtiene todas las líneas)
                {
                    "fields": [
                        "name",
                        "date",
                        "unit_amount",
                        "employee_id",
                        "project_id",
                        "task_id",
                        "create_date",
                    ],
                    "limit": 100,
                },
            ),
        )
        parsed_lines = [
            self._transform_odoo_to_detailed_domain(line)
            for line in odoo_timesheet_lines
        ]
        print(parsed_lines)
        return parsed_lines

    def delete(self, timesheet_line_id: int) -> bool:
        """Elimina una línea de hoja de tiempo de Odoo.

        Args:
            timesheet_line_id: ID de la línea de hoja de tiempo a eliminar

        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario
        """
        try:
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",
                "unlink",  # Método de Odoo para eliminar registros
                [[timesheet_line_id]],
            )
            return True
        except Exception:
            return False

    def get_by_id(self, timesheet_line_id: int) -> DetailedTimesheetLine:
        """Obtiene una línea de hoja de tiempo por su ID.

        Args:
            timesheet_line_id: ID de la línea de hoja de tiempo a obtener

        Returns:
            DetailedTimesheetLine: Línea de hoja de tiempo con detalles
        """

        odoo_data = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",
                "read",
                [timesheet_line_id],
                {
                    "fields": [
                        "id",
                        "name",
                        "date",
                        "unit_amount",
                        "employee_id",
                        "project_id",
                        "task_id",
                        "create_date",
                    ],
                },
            ),
        )
        if not odoo_data or len(odoo_data) == 0:
            raise ValueError("No se encontró la línea de timesheet")
        return self._transform_odoo_to_detailed_domain(odoo_data[0])
