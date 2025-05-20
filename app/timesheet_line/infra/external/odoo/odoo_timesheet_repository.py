from typing import List, Dict, Any, cast
from datetime import datetime, date
from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineRepository
from app.shared.infra.external.odoo.odoo_client import OdooConnection


class OdooTimesheetLineRepository(TimesheetLineRepository):
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
            task_id = int(raw_task_id[0])
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

    def all(self) -> List[TimesheetLine]:
        """Obtiene todas las líneas de hoja de tiempo de Odoo.

        Returns:
            List[TimesheetLine]: Lista de líneas de hoja de tiempo transformadas
        """
        odoo_timesheet_lines = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",  # Modelo de las líneas de hojas de tiempo
                "search_read",  # Método para buscar y leer registros
                [[]],  # Sin filtros (obtiene todas las líneas)
                {
                    "fields": [
                        "name",
                        "date",
                        "unit_amount",
                        "employee_id",
                        "project_id",
                        "task_id",
                    ],
                    "limit": 100,
                },
            ),
        )
        parsed_lines = [
            self._transform_odoo_to_domain(line) for line in odoo_timesheet_lines
        ]
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
