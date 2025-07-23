from typing import List
from app.users.domain.repositories import EmployeeGateway
from app.users.domain.models import Employee


class GetAllEmployeesUseCase:
    def __init__(self, employee_gateway: EmployeeGateway):
        self.gateway = employee_gateway

    def execute(self) -> List[Employee]:
        """
        Obtiene todos los empleados registrados en Odoo.

        Returns:
            List[Employee]: Lista de todos los empleados de Odoo
        """
        employees = self.gateway.all()
        return employees
