from datetime import date
from typing import Optional
from app.employee_price.domain.models import EmployeePrice
from app.employee_price.domain.repositories import EmployeePriceRepository


class SetEmployeeCostPerHourUseCase:
    """
    Caso de uso para establecer o actualizar el costo por hora del registro activo de un empleado.
    Busca el registro activo del usuario en la fecha actual y actualiza su costo por hora.
    """

    def __init__(self, employee_price_repository: EmployeePriceRepository):
        self.employee_price_repository = employee_price_repository

    def execute(
        self, user_id: int, cost_per_hour: float, check_date: Optional[date] = None
    ) -> Optional[EmployeePrice]:
        """
        Ejecuta la actualización del costo por hora para el registro activo de un usuario.

        Args:
            user_id: ID del usuario
            cost_per_hour: Nuevo costo por hora (debe ser > 0)
            check_date: Fecha para buscar el registro activo (por defecto, fecha actual)

        Returns:
            EmployeePrice actualizado o None si no se encuentra registro activo

        Raises:
            ValueError: Si el cost_per_hour es <= 0
        """
        # 1. Validar que el cost_per_hour sea válido
        if cost_per_hour <= 0:
            raise ValueError("El costo por hora debe ser mayor a 0")

        # 2. Obtener el registro activo del usuario
        if check_date is None:
            check_date = date.today()

        employee_price = self.employee_price_repository.get_active_by_user_id(
            user_id, check_date
        )

        if not employee_price:
            return None

        # 3. Validar que tenga ID
        if employee_price.id is None:
            return None

        # 4. Actualizar el cost_per_hour
        employee_price.cost_per_hour = cost_per_hour

        # 5. Guardar los cambios
        success = self.employee_price_repository.update(employee_price)

        if not success:
            return None

        # 6. Retornar el registro actualizado
        return self.employee_price_repository.get_by_id(employee_price.id)

