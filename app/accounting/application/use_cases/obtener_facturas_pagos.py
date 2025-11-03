"""Caso de uso para obtener facturas con información de pagos."""

import io
from datetime import date
from typing import List

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.accounting.domain.repositories import AccountingGateway
from app.accounting.domain.models import ProcessedInvoiceRow


class ObtenerFacturasPagosUseCase:
    """Caso de uso para obtener facturas de clientes con información de pagos."""

    def __init__(self, accounting_gateway: AccountingGateway):
        self.accounting_gateway = accounting_gateway

    def execute(
        self,
        date_from: date,
        date_to: date,
    ) -> io.BytesIO:
        """
        Ejecuta el caso de uso para obtener facturas con pagos y generar Excel.

        Args:
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período

        Returns:
            BytesIO: Buffer con el archivo Excel generado
        """
        # Obtener facturas del gateway
        invoices = self.accounting_gateway.get_customer_invoices(
            date_from=date_from,
            date_to=date_to,
        )

        # Procesar facturas y generar filas
        rows = self._process_invoices(invoices)

        # Generar Excel
        excel_buffer = self._generate_excel(rows)

        return excel_buffer

    def _process_invoices(self, invoices) -> List[ProcessedInvoiceRow]:
        """Procesa las facturas y genera filas con información de pagos."""
        rows = []

        for invoice in invoices:
            if invoice.payments:
                # Si hay pagos, crear una fila por cada pago
                for payment in invoice.payments:
                    row = ProcessedInvoiceRow(
                        cliente=invoice.partner_name,
                        numero_factura=invoice.name,
                        fecha_factura=invoice.invoice_date or "",
                        fecha_vencimiento=invoice.invoice_date_due or "",
                        fecha_cobro=payment.date,
                        monto_factura=invoice.amount_total,
                        monto_cobrado=payment.amount,
                        moneda=invoice.currency_name or "",
                    )
                    rows.append(row)
            else:
                # Si no hay pagos, crear una fila con monto cobrado = 0
                row = ProcessedInvoiceRow(
                    cliente=invoice.partner_name,
                    numero_factura=invoice.name,
                    fecha_factura=invoice.invoice_date or "",
                    fecha_vencimiento=invoice.invoice_date_due or "",
                    fecha_cobro="",
                    monto_factura=invoice.amount_total,
                    monto_cobrado=0.0,
                    moneda=invoice.currency_name or "",
                )
                rows.append(row)

        # Ordenar por fecha de factura y luego por número de factura
        rows.sort(key=lambda x: (x.fecha_factura, x.numero_factura))

        return rows

    def _generate_excel(self, rows: List[ProcessedInvoiceRow]) -> io.BytesIO:
        """
        Genera un archivo Excel con formato profesional.

        Args:
            rows: Lista de filas procesadas

        Returns:
            BytesIO: Buffer con el archivo Excel generado
        """
        # Crear workbook y hoja activa
        wb = Workbook()
        ws = wb.active
        if ws is None:
            raise ValueError("No se pudo crear la hoja de cálculo")
        ws.title = "Facturas y Pagos"

        # Definir headers
        headers = [
            "Cliente",
            "Número de Factura",
            "Moneda",
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
        header_alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

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
            cell.value = header  # type: ignore
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
            cell = ws.cell(row=row_num, column=1, value=row_data.cliente)
            cell.font = data_font
            cell.alignment = data_alignment_text
            cell.border = thin_border
            cell.fill = fill

            # Número de factura
            cell = ws.cell(row=row_num, column=2, value=row_data.numero_factura)
            cell.font = data_font
            cell.alignment = data_alignment_center
            cell.border = thin_border
            cell.fill = fill

            # Moneda
            cell = ws.cell(row=row_num, column=3, value=row_data.moneda)
            cell.font = data_font
            cell.alignment = data_alignment_center
            cell.border = thin_border
            cell.fill = fill

            # Fecha Factura
            cell = ws.cell(row=row_num, column=4, value=row_data.fecha_factura)
            cell.font = data_font
            cell.alignment = data_alignment_center
            cell.border = thin_border
            cell.fill = fill
            if row_data.fecha_factura:
                cell.number_format = "DD/MM/YYYY"

            # Fecha Vencimiento
            cell = ws.cell(row=row_num, column=5, value=row_data.fecha_vencimiento)
            cell.font = data_font
            cell.alignment = data_alignment_center
            cell.border = thin_border
            cell.fill = fill
            if row_data.fecha_vencimiento:
                cell.number_format = "DD/MM/YYYY"

            # Fecha Cobro
            cell = ws.cell(row=row_num, column=6, value=row_data.fecha_cobro)
            cell.font = data_font
            cell.alignment = data_alignment_center
            cell.border = thin_border
            cell.fill = fill
            if row_data.fecha_cobro:
                cell.number_format = "DD/MM/YYYY"

            # Monto Factura
            cell = ws.cell(row=row_num, column=7, value=row_data.monto_factura)
            cell.font = data_font
            cell.alignment = data_alignment_right
            cell.border = thin_border
            cell.fill = fill
            cell.number_format = "$#,##0.00"

            # Monto Cobrado
            cell = ws.cell(row=row_num, column=8, value=row_data.monto_cobrado)
            cell.font = data_font
            cell.alignment = data_alignment_right
            cell.border = thin_border
            cell.fill = fill
            cell.number_format = "$#,##0.00"

        # Ajustar anchos de columna
        column_widths = {
            "A": 40,  # Cliente
            "B": 25,  # Número de factura
            "C": 12,  # Moneda
            "D": 18,  # Fecha Factura
            "E": 20,  # Fecha Vencimiento
            "F": 18,  # Fecha Cobro
            "G": 18,  # Monto Factura
            "H": 18,  # Monto Cobrado
        }

        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width

        # Congelar la primera fila (headers)
        ws.freeze_panes = "A2"

        # Aplicar autofiltro
        if rows:
            ws.auto_filter.ref = f"A1:H{len(rows) + 1}"

        # Agregar fila de totales al final
        if rows:
            total_row = len(rows) + 2
            ws.cell(row=total_row, column=1, value="TOTALES")
            ws.cell(row=total_row, column=1).font = Font(
                name="Calibri", size=11, bold=True
            )
            ws.cell(row=total_row, column=1).fill = PatternFill(
                start_color="FFD966", end_color="FFD966", fill_type="solid"
            )
            ws.cell(row=total_row, column=1).border = thin_border

            # Suma de Monto Factura
            total_factura_cell = ws.cell(row=total_row, column=7)
            total_factura_cell.value = (  # type: ignore
                f"=SUMIF(B2:B{len(rows) + 1},B2:B{len(rows) + 1},G2:G{len(rows) + 1})"
            )
            total_factura_cell.font = Font(name="Calibri", size=11, bold=True)
            total_factura_cell.fill = PatternFill(
                start_color="FFD966", end_color="FFD966", fill_type="solid"
            )
            total_factura_cell.border = thin_border
            total_factura_cell.alignment = data_alignment_right
            total_factura_cell.number_format = "$#,##0.00"

            # Suma de Monto Cobrado
            total_cobrado_cell = ws.cell(row=total_row, column=8)
            total_cobrado_cell.value = f"=SUM(H2:H{len(rows) + 1})"  # type: ignore
            total_cobrado_cell.font = Font(name="Calibri", size=11, bold=True)
            total_cobrado_cell.fill = PatternFill(
                start_color="FFD966", end_color="FFD966", fill_type="solid"
            )
            total_cobrado_cell.border = thin_border
            total_cobrado_cell.alignment = data_alignment_right
            total_cobrado_cell.number_format = "$#,##0.00"

            # Rellenar celdas vacías de la fila de totales
            for col in range(2, 7):
                cell = ws.cell(row=total_row, column=col)
                cell.fill = PatternFill(
                    start_color="FFD966", end_color="FFD966", fill_type="solid"
                )
                cell.border = thin_border

        # Guardar en buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return output
