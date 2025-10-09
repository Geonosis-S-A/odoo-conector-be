from datetime import date
from typing import Optional

from app.employee_price.domain.models import EmployeePrice
from app.employee_price.domain.repositories import EmployeePriceRepository


class CreateEmployeePriceUseCase:
    """
    Caso de uso para crear un nuevo registro de precio de empleado.
    
    Si existe un registro activo previo para el usuario (con date_to vacío),
    automáticamente se cerrará ese registro actualizando su date_to con
    la fecha del día anterior al nuevo registro.
    """

    def __init__(self, employee_price_repository: EmployeePriceRepository):
        self.employee_price_repository = employee_price_repository

    def execute(
        self,
        user_id: int,
        date_from: date,
        cost_per_hour: Optional[float] = None,
    ) -> EmployeePrice:
        """
        Ejecuta la creación de un nuevo registro de precio de empleado.
        
        Si existe un registro activo previo (date_to vacío), lo cierra automáticamente
        estableciendo su date_to al día anterior del nuevo registro.

        Args:
            user_id: ID del usuario/empleado
            date_from: Fecha de inicio de vigencia del precio
            cost_per_hour: Costo por hora del empleado (opcional, debe ser mayor a 0)

        Returns:
            EmployeePrice: El registro de precio creado con su ID asignado

        Raises:
            ValueError: Si el cost_per_hour es menor o igual a 0
        """
        # Validación: cost_per_hour debe ser mayor a 0 si se proporciona
        if cost_per_hour is not None and cost_per_hour <= 0:
            raise ValueError(
                f"El costo por hora debe ser mayor a 0, se recibió: {cost_per_hour}"
            )

        # Buscar si existe un registro abierto (date_to = NULL) para este usuario
        open_record = self.employee_price_repository.get_open_record_by_user_id(
            user_id=user_id
        )

        # Si existe un registro abierto, validar y cerrarlo
        if open_record:
            open_record.date_to = date_from
            self.employee_price_repository.update(open_record)

        # Crear la entidad de dominio para el nuevo registro
        employee_price = EmployeePrice.from_request(
            user_id=user_id,
            date_from=date_from,
            cost_per_hour=cost_per_hour,
            date_to=None,
        )

        # Guardar en el repositorio
        created_employee_price = self.employee_price_repository.save(employee_price)

        return created_employee_price

