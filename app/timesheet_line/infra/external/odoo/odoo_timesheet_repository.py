from typing import List, Dict, Any, cast
from app.timesheet_line.domain.models import TimesheetLine
from app.timesheet_line.domain.repositories import TimesheetLineRepository
from app.timesheet_line.infra.external.odoo.get_odoo import OdooConnection


class OdooTimesheetLineRepository(TimesheetLineRepository):

    def __init__(self, odoo_client: OdooConnection) -> None:
        self.odoo_client = odoo_client

    def _transform_odoo_to_domain(self, odoo_data: Dict[str, Any]) -> TimesheetLine:
        """Transforma los datos de Odoo al modelo de dominio.
        
        Args:
            odoo_data: Datos de la línea de hoja de tiempo de Odoo
            
        Returns:
            TimesheetLine: Modelo de dominio transformado
        """
        return TimesheetLine(
            name=odoo_data.get("name", ""),
            employee_id=odoo_data.get("employee_id", [0, ""])[0],
            project_id=odoo_data.get("project_id", [0, ""])[0],
            hours=float(odoo_data.get("unit_amount", 0.0)),
            date=odoo_data.get("date", "")
        )
    
    def create(self, timesheet_line: TimesheetLine) -> None:
        """Crea una nueva línea de hoja de tiempo en Odoo.
        
        Args:
            timesheet_line: La línea de hoja de tiempo a crear
        """
        self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "account.analytic.line",  # Modelo de las líneas de hojas de tiempo
            "create",  # Método para crear un nuevo registro
            [{
                "name": timesheet_line.name,
                "date": timesheet_line.date,
                "unit_amount": timesheet_line.hours,
                "employee_id": timesheet_line.employee_id,
                "project_id": timesheet_line.project_id
            }]
        )

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
                        "project_id"
                    ],
                    "limit": 100
                }
            )
        )
        parsed_lines = [self._transform_odoo_to_domain(line) for line in odoo_timesheet_lines]
        return parsed_lines
