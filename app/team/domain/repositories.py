from abc import ABC, abstractmethod
from typing import List, Optional

from app.team.domain.models import Team, TeamMember


class TeamRepository(ABC):

    @abstractmethod
    def create(self, team: Team) -> Team: ...

    @abstractmethod
    def get_by_id(self, team_id: int) -> Optional[Team]: ...

    @abstractmethod
    def get_all(self) -> List[Team]: ...

    @abstractmethod
    def get_by_employee_odoo_id(self, employee_odoo_id: int) -> List[Team]:
        """Retorna todos los equipos donde el empleado es miembro (cualquier rol)."""
        ...

    @abstractmethod
    def update(self, team: Team) -> Team: ...

    @abstractmethod
    def delete(self, team_id: int) -> bool: ...

    @abstractmethod
    def add_member(self, member: TeamMember) -> TeamMember: ...

    @abstractmethod
    def update_member(self, member: TeamMember) -> TeamMember: ...

    @abstractmethod
    def remove_member(self, team_id: int, employee_odoo_id: int) -> bool: ...

    @abstractmethod
    def get_member(self, team_id: int, employee_odoo_id: int) -> Optional[TeamMember]: ...

    @abstractmethod
    def get_member_employee_ids(self, team_id: int) -> List[int]:
        """Retorna los employee_odoo_id de todos los miembros de un equipo."""
        ...

    @abstractmethod
    def get_member_record(self, employee_odoo_id: int) -> Optional[TeamMember]:
        """Retorna el registro de miembro del empleado (busca en todos los equipos)."""
        ...

    @abstractmethod
    def get_team_member_ids_by_any_leader(self, employee_odoo_id: int) -> List[int]:
        """
        Si el empleado es leader/pm/sub_leader (con view) en algún equipo,
        retorna los employee_odoo_id de los demás miembros de ese equipo.
        Retorna lista vacía si no pertenece a ningún equipo con acceso de vista.
        """
        ...
