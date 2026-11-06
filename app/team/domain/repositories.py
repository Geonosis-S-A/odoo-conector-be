from abc import ABC, abstractmethod
from typing import List, Optional

from app.team.domain.models import TeamMemberPermission


class TeamPermissionRepository(ABC):
    """Persistencia de los permisos (líder, miembro) -> nivel."""

    @abstractmethod
    def get(
        self, leader_employee_odoo_id: int, member_employee_odoo_id: int
    ) -> Optional[TeamMemberPermission]: ...

    @abstractmethod
    def list_by_leader(
        self, leader_employee_odoo_id: int
    ) -> List[TeamMemberPermission]: ...

    @abstractmethod
    def list_by_member(
        self, member_employee_odoo_id: int
    ) -> List[TeamMemberPermission]: ...

    @abstractmethod
    def upsert(self, permission: TeamMemberPermission) -> TeamMemberPermission:
        """Crea o actualiza el permiso para el par (líder, miembro)."""
        ...

    @abstractmethod
    def delete(
        self, leader_employee_odoo_id: int, member_employee_odoo_id: int
    ) -> bool: ...
