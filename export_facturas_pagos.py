#!/usr/bin/env python3
"""
Script para exportar facturas de clientes con información de pagos desde Odoo.

Extrae facturas posteadas entre 2025-06-01 y 2025-07-31 y genera un Excel
con información de cliente, factura, fechas y montos cobrados.

Uso:
    python export_facturas_pagos.py --url https://mi-odoo.com --db PROD --username user@example.com --password ********

    O usando variables de entorno:
    export ODOO_URL=https://mi-odoo.com
    export ODOO_DB=PROD
    export ODOO_USERNAME=user@example.com
    export ODOO_PASSWORD=********
    python export_facturas_pagos.py
"""

import argparse
import json
import os
import sys
import xmlrpc.client
from datetime import datetime
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def parse_arguments() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Exportar facturas de clientes con pagos desde Odoo"
    )
    parser.add_argument(
        "--url",
        default=os.getenv("ODOO_URL"),
        help="URL base de Odoo (ej: https://mi-odoo.com)",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("ODOO_DB"),
        help="Nombre de la base de datos",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("ODOO_USERNAME"),
        help="Usuario de Odoo",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ODOO_PASSWORD"),
        help="Contraseña de Odoo",
    )

    args = parser.parse_args()

    # Validar que todos los parámetros requeridos estén presentes
    if not all([args.url, args.db, args.username, args.password]):
        parser.error(
            "Todos los parámetros son requeridos: --url, --db, --username, --password\n"
            "O configura las variables de entorno: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD"
        )

    return args


def authenticate_odoo(url: str, db: str, username: str, password: str) -> tuple:
    """
    Autentica con Odoo y retorna el uid y los objetos common/models.

    Args:
        url: URL base de Odoo
        db: Nombre de la base de datos
        username: Usuario
        password: Contraseña

    Returns:
        Tupla (uid, models) donde models es el proxy para ejecutar llamadas
    """
    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid = common.authenticate(db, username, password, {})

        if not uid:
            raise Exception("Autenticación fallida. Verifica las credenciales.")

        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        return uid, models
    except Exception as e:
        print(f"Error al conectar con Odoo: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_invoices(
    models: xmlrpc.client.ServerProxy,
    db: str,
    uid: int,
    password: str,
    date_from: str = "2025-06-01",
    date_to: str = "2025-07-31",
) -> List[Dict[str, Any]]:
    """
    Obtiene facturas de clientes posteadas en el rango de fechas especificado.

    Args:
        models: Proxy de XML-RPC para llamadas al modelo
        db: Nombre de la base de datos
        uid: ID de usuario autenticado
        password: Contraseña
        date_from: Fecha de inicio (formato YYYY-MM-DD)
        date_to: Fecha de fin (formato YYYY-MM-DD)

    Returns:
        Lista de diccionarios con datos de facturas
    """
    domain = [
        ("move_type", "in", ["out_invoice", "out_refund"]),
        ("state", "=", "posted"),
        ("invoice_date", ">=", date_from),
        ("invoice_date", "<=", date_to),
    ]

    fields = [
        "partner_id",
        "name",
        "invoice_date",
        "invoice_date_due",
        "amount_total",
        "move_type",
        "state",
        "invoice_payments_widget",
    ]

    try:
        invoices = models.execute_kw(
            db,
            uid,
            password,
            "account.move",
            "search_read",
            [domain],
            {"fields": fields},
        )
        return invoices
    except Exception as e:
        print(f"Error al obtener facturas: {e}", file=sys.stderr)
        sys.exit(1)


def parse_payment_widget(widget_data: Any) -> List[Dict[str, Any]]:
    """
    Parsea el campo invoice_payments_widget para extraer información de pagos.

    Args:
        widget_data: Datos del widget (puede ser string JSON, dict o None)

    Returns:
        Lista de pagos aplicados a la factura
    """
    if not widget_data:
        return []

    try:
        # Si viene como string, parsearlo como JSON
        if isinstance(widget_data, str):
            widget = json.loads(widget_data)
        else:
            widget = widget_data

        # Extraer la lista de pagos del contenido
        if isinstance(widget, dict) and "content" in widget:
            return widget["content"]

        return []
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def process_invoices(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Procesa las facturas y genera filas con información de pagos.

    Args:
        invoices: Lista de facturas obtenidas de Odoo

    Returns:
        Lista de filas procesadas para el CSV
    """
    rows = []

    for invoice in invoices:
        # Extraer datos básicos de la factura
        cliente = (
            invoice.get("partner_id", [None, ""])[1]
            if invoice.get("partner_id")
            else ""
        )
        numero_factura = invoice.get("name", "")
        fecha_factura = invoice.get("invoice_date", "")
        fecha_vencimiento = invoice.get("invoice_date_due", "")
        monto_factura = invoice.get("amount_total", 0.0)

        # Parsear pagos del widget
        payments = parse_payment_widget(invoice.get("invoice_payments_widget"))

        if payments:
            # Si hay pagos, crear una fila por cada pago
            for payment in payments:
                row = {
                    "Cliente": cliente,
                    "Número de factura": numero_factura,
                    "Fecha Factura": fecha_factura or "",
                    "Fecha Vencimiento": fecha_vencimiento or "",
                    "Fecha Cobro": payment.get("date", ""),
                    "Monto Factura": monto_factura,
                    "Monto Cobrado": payment.get("amount", 0.0),
                }
                rows.append(row)
        else:
            # Si no hay pagos, crear una fila con monto cobrado = 0
            row = {
                "Cliente": cliente,
                "Número de factura": numero_factura,
                "Fecha Factura": fecha_factura or "",
                "Fecha Vencimiento": fecha_vencimiento or "",
                "Fecha Cobro": "",
                "Monto Factura": monto_factura,
                "Monto Cobrado": 0.0,
            }
            rows.append(row)

    # Ordenar por Fecha Factura y luego por Número de factura
    rows.sort(key=lambda x: (x["Fecha Factura"], x["Número de factura"]))

    return rows


def write_excel(
    rows: List[Dict[str, Any]], filename: str = "facturas_pagos.xlsx"
) -> None:
    """
    Escribe las filas procesadas como un archivo Excel con formato profesional.

    Args:
        rows: Lista de filas procesadas
        filename: Nombre del archivo Excel a generar
    """
    # Crear workbook y hoja activa
    wb = Workbook()
    ws = wb.active
    ws.title = "Facturas y Pagos"

    # Definir headers
    headers = [
        "Cliente",
        "Número de Factura",
        "Fecha Factura",
        "Fecha Vencimiento",
        "Fecha Cobro",
        "Monto Factura",
        "Monto Cobrado",
    ]

    # Estilos para el header
    header_font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="2E75B6", end_color="2E75B6", fill_type="solid"
    )
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Bordes
    thin_border = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000"),
    )

    # Escribir headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Estilos para los datos
    data_font = Font(name="Calibri", size=11)
    data_alignment_text = Alignment(horizontal="left", vertical="center")
    data_alignment_center = Alignment(horizontal="center", vertical="center")
    data_alignment_right = Alignment(horizontal="right", vertical="center")

    # Fills alternos para las filas
    fill_white = PatternFill(
        start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"
    )
    fill_light = PatternFill(
        start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"
    )

    # Escribir datos
    for row_num, row_data in enumerate(rows, 2):
        fill = fill_light if row_num % 2 == 0 else fill_white

        # Cliente
        cell = ws.cell(row=row_num, column=1, value=row_data.get("Cliente", ""))
        cell.font = data_font
        cell.alignment = data_alignment_text
        cell.border = thin_border
        cell.fill = fill

        # Número de factura
        cell = ws.cell(
            row=row_num, column=2, value=row_data.get("Número de factura", "")
        )
        cell.font = data_font
        cell.alignment = data_alignment_center
        cell.border = thin_border
        cell.fill = fill

        # Fecha Factura
        fecha_factura = row_data.get("Fecha Factura", "")
        cell = ws.cell(row=row_num, column=3, value=fecha_factura)
        cell.font = data_font
        cell.alignment = data_alignment_center
        cell.border = thin_border
        cell.fill = fill
        if fecha_factura:
            cell.number_format = "DD/MM/YYYY"

        # Fecha Vencimiento
        fecha_venc = row_data.get("Fecha Vencimiento", "")
        cell = ws.cell(row=row_num, column=4, value=fecha_venc)
        cell.font = data_font
        cell.alignment = data_alignment_center
        cell.border = thin_border
        cell.fill = fill
        if fecha_venc:
            cell.number_format = "DD/MM/YYYY"

        # Fecha Cobro
        fecha_cobro = row_data.get("Fecha Cobro", "")
        cell = ws.cell(row=row_num, column=5, value=fecha_cobro)
        cell.font = data_font
        cell.alignment = data_alignment_center
        cell.border = thin_border
        cell.fill = fill
        if fecha_cobro:
            cell.number_format = "DD/MM/YYYY"

        # Monto Factura
        monto_factura = row_data.get("Monto Factura", 0.0)
        cell = ws.cell(row=row_num, column=6, value=monto_factura)
        cell.font = data_font
        cell.alignment = data_alignment_right
        cell.border = thin_border
        cell.fill = fill
        cell.number_format = "$#,##0.00"

        # Monto Cobrado
        monto_cobrado = row_data.get("Monto Cobrado", 0.0)
        cell = ws.cell(row=row_num, column=7, value=monto_cobrado)
        cell.font = data_font
        cell.alignment = data_alignment_right
        cell.border = thin_border
        cell.fill = fill
        cell.number_format = "$#,##0.00"

    # Ajustar anchos de columna
    column_widths = {
        "A": 40,  # Cliente
        "B": 25,  # Número de factura
        "C": 18,  # Fecha Factura
        "D": 20,  # Fecha Vencimiento
        "E": 18,  # Fecha Cobro
        "F": 18,  # Monto Factura
        "G": 18,  # Monto Cobrado
    }

    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    # Congelar la primera fila (headers)
    ws.freeze_panes = "A2"

    # Aplicar autofiltro
    ws.auto_filter.ref = f"A1:G{len(rows) + 1}"

    # Agregar fila de totales al final
    total_row = len(rows) + 2
    ws.cell(row=total_row, column=1, value="TOTALES")
    ws.cell(row=total_row, column=1).font = Font(name="Calibri", size=11, bold=True)
    ws.cell(row=total_row, column=1).fill = PatternFill(
        start_color="FFD966", end_color="FFD966", fill_type="solid"
    )
    ws.cell(row=total_row, column=1).border = thin_border

    # Suma de Monto Factura (solo valores únicos para evitar duplicados)
    total_factura_cell = ws.cell(row=total_row, column=6)
    total_factura_cell.value = (
        f"=SUMIF(B2:B{len(rows) + 1},B2:B{len(rows) + 1},F2:F{len(rows) + 1})"
    )
    total_factura_cell.font = Font(name="Calibri", size=11, bold=True)
    total_factura_cell.fill = PatternFill(
        start_color="FFD966", end_color="FFD966", fill_type="solid"
    )
    total_factura_cell.border = thin_border
    total_factura_cell.alignment = data_alignment_right
    total_factura_cell.number_format = "$#,##0.00"

    # Suma de Monto Cobrado
    total_cobrado_cell = ws.cell(row=total_row, column=7)
    total_cobrado_cell.value = f"=SUM(G2:G{len(rows) + 1})"
    total_cobrado_cell.font = Font(name="Calibri", size=11, bold=True)
    total_cobrado_cell.fill = PatternFill(
        start_color="FFD966", end_color="FFD966", fill_type="solid"
    )
    total_cobrado_cell.border = thin_border
    total_cobrado_cell.alignment = data_alignment_right
    total_cobrado_cell.number_format = "$#,##0.00"

    # Rellenar celdas vacías de la fila de totales
    for col in range(2, 6):
        cell = ws.cell(row=total_row, column=col)
        cell.fill = PatternFill(
            start_color="FFD966", end_color="FFD966", fill_type="solid"
        )
        cell.border = thin_border

    # Guardar archivo
    wb.save(filename)
    print(f"✓ Archivo generado exitosamente: {filename}")
    print(f"  Total de filas: {len(rows)}")
    print("  Rango de fechas: 2025-06-01 a 2025-07-31")


def main():
    """Función principal del script."""
    # Parsear argumentos
    args = parse_arguments()

    # Autenticar con Odoo
    uid, models = authenticate_odoo(
        args.url,
        args.db,
        args.username,
        args.password,
    )

    # Obtener facturas
    invoices = fetch_invoices(
        models,
        args.db,
        uid,
        args.password,
    )

    # Procesar facturas y extraer información de pagos
    rows = process_invoices(invoices)

    # Generar nombre de archivo con fecha actual
    fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"facturas_pagos_{fecha_actual}.xlsx"

    # Escribir Excel con formato
    write_excel(rows, filename)


if __name__ == "__main__":
    main()
