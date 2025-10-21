"""Routers de la API para el módulo de accounting."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.accounting.application.use_cases.obtener_facturas_pagos import (
    ObtenerFacturasPagosUseCase,
)
from app.accounting.domain.repositories import AccountingGateway
from app.accounting.infra.external.odoo_accounting_gateway import (
    OdooAccountingGateway,
)
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import user_has_role, Roles

router = APIRouter(prefix="/accounting", tags=["accounting"])


def get_accounting_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> AccountingGateway:
    """Dependencia para obtener el gateway de accounting."""
    try:
        return OdooAccountingGateway(odoo_connection)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de accounting"
        )


@router.get("/export-facturas-pagos")
async def export_facturas_pagos(
    date_from: date = Query(..., description="Fecha de inicio del rango (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha de fin del rango (YYYY-MM-DD)"),
    accounting_gateway: AccountingGateway = Depends(get_accounting_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Exporta facturas de clientes con información de pagos como archivo Excel.

    Args:
        date_from: Fecha de inicio del período
        date_to: Fecha de fin del período
        accounting_gateway: Gateway de accounting (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        StreamingResponse: Archivo Excel con las facturas y pagos
    """
    # Validar permisos - Solo usuarios con rol approver pueden exportar
    mail = current_user["user_email"]
    mail = mail.lower().strip()
    allowed_mails = [
        "cintia.papapietro@geonosis.com.ar",
        "camila.perez@geonosis.com.ar",
    ]
    if mail not in allowed_mails:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para exportar facturas y pagos",
        )
    try:
        # Validar que date_from no sea posterior a date_to
        if date_from > date_to:
            raise HTTPException(
                status_code=400,
                detail="La fecha de inicio no puede ser posterior a la fecha de fin",
            )

        # Crear y ejecutar caso de uso
        use_case = ObtenerFacturasPagosUseCase(accounting_gateway)
        excel_buffer = use_case.execute(date_from, date_to)

        # Generar nombre de archivo con las fechas
        filename = f"facturas_pagos_{date_from}_{date_to}.xlsx"

        # Retornar como streaming response
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise
