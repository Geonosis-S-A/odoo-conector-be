from abc import ABC, abstractmethod
from typing import List, Optional
from app.timesheet_templates.domain.models import TimesheetTemplate


class TimesheetTemplateRepository(ABC):
    """Interface del repositorio para templates de carga de timesheets."""

    @abstractmethod
    def create(self, template: TimesheetTemplate) -> TimesheetTemplate:
        """Crea un nuevo template.

        Args:
            template: El template a guardar

        Returns:
            TimesheetTemplate: El template guardado con su ID asignado
        """
        pass

    @abstractmethod
    def list_by_user(self, user_id: int) -> List[TimesheetTemplate]:
        """Lista todos los templates de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            List[TimesheetTemplate]: Lista de templates del usuario
        """
        pass

    @abstractmethod
    def delete(self, template_id: int, user_id: int) -> bool:
        """Elimina un template.

        Args:
            template_id: ID del template a eliminar
            user_id: ID del usuario (para validar ownership)

        Returns:
            bool: True si se eliminó correctamente

        Raises:
            ValueError: Si el template no existe o no pertenece al usuario
        """
        pass

    @abstractmethod
    def get_by_id(self, template_id: int) -> Optional[TimesheetTemplate]:
        """Obtiene un template por su ID.

        Args:
            template_id: ID del template

        Returns:
            TimesheetTemplate | None: El template o None si no existe
        """
        pass
