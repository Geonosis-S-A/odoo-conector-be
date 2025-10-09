from typing import List

from app.employee_price.domain.models import EmployeePrice
from app.employee_price.domain.repositories import EmployeePriceRepository


class GetEmployeePriceHistoryUseCase:
    """
    Caso de uso para obtener el historial completo de precios de un empleado.
    """

    def __init__(self, employee_price_repository: EmployeePriceRepository):
        self.employee_price_repository = employee_price_repository

    def execute(self, employee_id: int) -> List[EmployeePrice]:
        """
        Ejecuta la obtención del historial de precios de un empleado.

        Args:
            employee_id: ID del usuario/empleado

        Returns:
            Lista de registros de EmployeePrice ordenados por fecha (más reciente primero)

        Raises:
            ValueError: Si el employee_id es inválido
        """

        # Obtener todos los registros del usuario
        price_history = self.employee_price_repository.get_by_user_id(employee_id)

        return price_history

