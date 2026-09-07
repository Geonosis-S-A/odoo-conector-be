from fastapi import Depends
from sqlmodel import Session

from app.shared.infra.db.session import get_db
from app.shared.infra.external.odoo.odoo_client import (
    OdooConnection,
    get_odoo_connection_dependency,
)
from app.team.application.team_access import TeamAccessService
from app.team.infra.db.repositories import SQLModelTeamPermissionRepository
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway


def get_permission_repository(
    db: Session = Depends(get_db),
) -> SQLModelTeamPermissionRepository:
    return SQLModelTeamPermissionRepository(db)


def get_team_access_service(
    db: Session = Depends(get_db),
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TeamAccessService:
    return TeamAccessService(
        employee_gateway=OdooEmployeeGateway(odoo_connection),
        timesheet_line_gateway=OdooTimesheetLineGateway(odoo_connection),
        permission_repo=SQLModelTeamPermissionRepository(db),
    )
