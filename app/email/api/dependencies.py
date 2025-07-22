from app.email.infra.email_service import ResendEmailService
from fastapi import Depends, HTTPException
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)
from app.timesheet_line.domain.repositories import TimesheetLineGateway


def get_email_service_dependency() -> ResendEmailService:
    """Dependencia para obtener el servicio de email"""
    return ResendEmailService()


def get_timesheet_line_gateway_dependency(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TimesheetLineGateway:
    return OdooTimesheetLineGateway(odoo_connection)