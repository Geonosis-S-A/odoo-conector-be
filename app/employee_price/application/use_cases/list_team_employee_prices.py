from typing import List, Dict, Any

from app.employee_price.domain.repositories import EmployeePriceRepository
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway


class ListTeamEmployeePricesUseCase:
    """
    Caso de uso para listar los precios de empleados del equipo de un usuario.
    """

    def __init__(
        self,
        employee_price_repository: EmployeePriceRepository,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_gateway: EmployeeGateway,
    ):
        self.employee_price_repository = employee_price_repository
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_gateway = employee_gateway
    def execute(
        self, user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la obtención de precios de empleados del equipo.
        
        Obtiene únicamente los registros abiertos (date_to = NULL) de cada empleado.

        Args:
            user_id: ID del usuario que hace la petición

        Returns:
            Lista de diccionarios con información de cada miembro del equipo y su registro abierto

        Raises:
            ValueError: Si no se puede obtener los usuarios del equipo
        """
        # Obtener los miembros del equipo desde Odoo
        employee_id = self.employee_gateway.get_by_id(user_id)
        if employee_id is None:
            raise ValueError("El usuario no tiene un empleado asociado")
        team_users = self.timesheet_line_gateway.get_team_users(user_id, employee_id.id)

        if not team_users:
            return []

        # Obtener los IDs de empleados del equipo
        team_employee_ids = [user["id"] for user in team_users]

        # Crear un mapa de employee_id a datos del usuario
        employee_data_map = {user["id"]: user for user in team_users}

        # Lista para almacenar los resultados
        result = []

        # Para cada empleado del equipo, buscar su registro abierto (date_to = NULL)
        for employee_id in team_employee_ids:
            # Obtener el registro abierto del empleado (sin date_to)
            open_record = self.employee_price_repository.get_open_record_by_user_id(
                user_id=employee_id
            )

            # Obtener datos del usuario desde el mapa
            user_data = employee_data_map.get(employee_id, {})

            # Construir el resultado para este empleado
            employee_info = {
                "employee_id": employee_id,
                "name": user_data.get("name", ""),
                "work_email": user_data.get("work_email", ""),
                "cost_per_hour": open_record.cost_per_hour if open_record else None,
                "date_from": open_record.date_from if open_record else None,
                "date_to": open_record.date_to if open_record else None,
            }

            result.append(employee_info)

        return result

