from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from app.personal_time.domain.models import HumandTimeOffRequest


class HumandGateway(ABC):
    """Gateway abstracto para operaciones con la API de HUMAND."""

    @abstractmethod
    def get_all_timeoff_requests(
        self,
        page: int = 1,
        limit: int = 500,
        states: Optional[List[str]] = None,
        policy_type_ids: Optional[List[str]] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        resolution_from_date: Optional[date] = None,
        resolution_to_date: Optional[date] = None,
        created_at_since: Optional[date] = None,
    ) -> List[HumandTimeOffRequest]:
        """Obtiene todas las solicitudes de tiempo personal desde HUMAND.

        Args:
            page: Página para paginación (default: 1)
            limit: Límite de resultados por página (default: 50)
            states: Lista de estados para filtrar (ej: ["approved", "pending", "rejected"])
            policy_type_ids: Lista de IDs de tipos de política para filtrar
            from_date: Fecha de inicio del filtro
            to_date: Fecha de fin del filtro
            resolution_from_date: Fecha de inicio de resolución
            resolution_to_date: Fecha de fin de resolución
            created_at_since: Filtrar por fecha de creación desde

        Returns:
            List[HumandTimeOffRequest]: Lista de solicitudes de HUMAND

        Raises:
            Exception: Si hay un error al obtener las solicitudes de HUMAND
        """
        pass

