from typing import List, Optional

from sqlmodel import Session, select

from app.team.domain.models import PermissionLevel, TeamMemberPermission
from app.team.domain.repositories import TeamPermissionRepository
from app.team.infra.db.models import TeamMemberPermissionModel


def _to_domain(m: TeamMemberPermissionModel) -> TeamMemberPermission:
    return TeamMemberPermission(
        id=m.id,
        leader_employee_odoo_id=m.leader_employee_odoo_id,
        member_employee_odoo_id=m.member_employee_odoo_id,
        level=PermissionLevel(m.level),
        created_at=m.created_at,
    )


class SQLModelTeamPermissionRepository(TeamPermissionRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def _find(
        self, leader_employee_odoo_id: int, member_employee_odoo_id: int
    ) -> Optional[TeamMemberPermissionModel]:
        return self.db.exec(
            select(TeamMemberPermissionModel).where(
                TeamMemberPermissionModel.leader_employee_odoo_id
                == leader_employee_odoo_id,
                TeamMemberPermissionModel.member_employee_odoo_id
                == member_employee_odoo_id,
            )
        ).first()

    def get(
        self, leader_employee_odoo_id: int, member_employee_odoo_id: int
    ) -> Optional[TeamMemberPermission]:
        m = self._find(leader_employee_odoo_id, member_employee_odoo_id)
        return _to_domain(m) if m is not None else None

    def list_by_leader(
        self, leader_employee_odoo_id: int
    ) -> List[TeamMemberPermission]:
        rows = self.db.exec(
            select(TeamMemberPermissionModel).where(
                TeamMemberPermissionModel.leader_employee_odoo_id
                == leader_employee_odoo_id
            )
        ).all()
        return [_to_domain(m) for m in rows]

    def list_by_member(
        self, member_employee_odoo_id: int
    ) -> List[TeamMemberPermission]:
        rows = self.db.exec(
            select(TeamMemberPermissionModel).where(
                TeamMemberPermissionModel.member_employee_odoo_id
                == member_employee_odoo_id
            )
        ).all()
        return [_to_domain(m) for m in rows]

    def upsert(self, permission: TeamMemberPermission) -> TeamMemberPermission:
        m = self._find(
            permission.leader_employee_odoo_id, permission.member_employee_odoo_id
        )
        if m is None:
            m = TeamMemberPermissionModel(
                leader_employee_odoo_id=permission.leader_employee_odoo_id,
                member_employee_odoo_id=permission.member_employee_odoo_id,
                level=permission.level.value,
            )
        else:
            m.level = permission.level.value
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return _to_domain(m)

    def delete(
        self, leader_employee_odoo_id: int, member_employee_odoo_id: int
    ) -> bool:
        m = self._find(leader_employee_odoo_id, member_employee_odoo_id)
        if m is None:
            return False
        self.db.delete(m)
        self.db.commit()
        return True
