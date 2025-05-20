from typing import List, Dict, Any, cast
from app.shared.infra.external.odoo.odoo_client import OdooConnection
from app.users.domain.repositories import EmployeeGateway
from app.users.domain.models import Employee


class OdooEmployeeGateway(EmployeeGateway):
    def __init__(self, odoo_client: OdooConnection) -> None:
        self.odoo_client = odoo_client

    def _transform_odoo_to_domain(self, odoo_data: Dict[str, Any]) -> Employee:
        """Transforma los datos de Odoo al modelo de dominio."""
        work_email = odoo_data.get("work_email")
        if not work_email or not isinstance(work_email, str) or "@" not in work_email:
            # Si no hay email válido, usamos un email temporal basado en el ID
            work_email = f"employee_{odoo_data.get('id')}@temporary.com"

        return Employee(
            id=odoo_data.get("id"),
            email=work_email,
            full_name=odoo_data.get("name", ""),
        )

    def all(self) -> List[Employee]:
        """Obtiene todos los empleados de Odoo.

        Returns:
            List[User]: Lista de empleados transformados al modelo de dominio
        """
        odoo_employees = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "hr.employee",  # Modelo de empleados en Odoo
                "search_read",  # Método para buscar y leer registros
                [[]],  # Sin filtros (obtiene todos los empleados)
                {
                    "fields": ["id", "name", "work_email"],
                    "limit": 100,
                },
            ),
        )
        parsed_employees = [
            self._transform_odoo_to_domain(employee) for employee in odoo_employees
        ]
        return parsed_employees
