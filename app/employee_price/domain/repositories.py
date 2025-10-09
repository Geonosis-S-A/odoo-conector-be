from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from app.employee_price.domain.models import EmployeePrice


class EmployeePriceRepository(ABC):
    """Interfaz para el repositorio de precios de empleados"""

    @abstractmethod
    def save(self, employee_price: EmployeePrice) -> EmployeePrice:
        """Guarda un nuevo registro de precio de empleado"""
        ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[EmployeePrice]:
        """Obtiene un registro por su ID"""
        ...

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> List[EmployeePrice]:
        """Obtiene todos los registros de precio de un usuario"""
        ...

    @abstractmethod
    def get_active_by_user_id(
        self, user_id: int, check_date: Optional[date] = None
    ) -> Optional[EmployeePrice]:
        """
        Obtiene el precio activo de un usuario en una fecha específica.
        Si no se proporciona fecha, usa la fecha actual.
        """
        ...

    @abstractmethod
    def get_open_record_by_user_id(self, user_id: int) -> Optional[EmployeePrice]:
        """
        Obtiene el registro abierto (sin date_to) de un usuario.
        Este método es útil para encontrar el registro que debe cerrarse
        al crear un nuevo registro de precio.
        
        Returns:
            El registro con date_to = NULL si existe, None en caso contrario
        """
        ...

    @abstractmethod
    def get_all(self) -> List[EmployeePrice]:
        """Obtiene todos los registros de precios"""
        ...

    @abstractmethod
    def update(self, employee_price: EmployeePrice) -> bool:
        """Actualiza un registro existente"""
        ...

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Elimina un registro por su ID"""
        ...

    @abstractmethod
    def get_all_active(self, check_date: Optional[date] = None) -> List[EmployeePrice]:
        """
        Obtiene todos los precios activos en una fecha específica.
        Si no se proporciona fecha, usa la fecha actual.
        """
        ...

