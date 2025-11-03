"""Implementación del gateway de accounting para Odoo."""

import json
from typing import List, Dict, Any, cast
from datetime import date

from app.accounting.domain.repositories import AccountingGateway
from app.accounting.domain.models import Invoice, Payment
from app.shared.infra.external.odoo.odoo_client import OdooConnection


class OdooAccountingGateway(AccountingGateway):
    """Implementación del gateway de accounting que se conecta a Odoo."""

    def __init__(self, odoo_client: OdooConnection) -> None:
        self.odoo_client = odoo_client

    def _get_currencies_map(self, currency_ids: List[int]) -> Dict[int, str]:
        """
        Obtiene los nombres de las monedas desde Odoo para los currency_ids dados.

        Args:
            currency_ids: Lista de IDs de monedas

        Returns:
            Diccionario mapeando currency_id -> currency_name
        """
        if not currency_ids:
            return {}

        # Consultar res.currency para obtener los nombres
        currencies_data = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "res.currency",
                "search_read",
                [[("id", "in", currency_ids)]],
                {"fields": ["id", "name"]},
            ),
        )

        # Crear diccionario de mapeo
        return {curr["id"]: curr["name"] for curr in currencies_data}

    def _parse_payment_widget(self, widget_data: Any) -> List[Payment]:
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
                payments_data = widget["content"]
                return [
                    Payment(
                        date=payment.get("date", ""),
                        amount=payment.get("amount", 0.0),
                        payment_id=payment.get("payment_id"),
                    )
                    for payment in payments_data
                ]

            return []
        except (json.JSONDecodeError, TypeError, KeyError):
            return []

    def get_customer_invoices(
        self,
        date_from: date,
        date_to: date,
    ) -> List[Invoice]:
        """
        Obtiene facturas de clientes posteadas en el rango de fechas especificado.

        Args:
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período

        Returns:
            Lista de facturas con información de pagos
        """
        # Construir dominio de filtros para Odoo
        domain = [
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("state", "=", "posted"),
            ("invoice_date", ">=", date_from.isoformat()),
            ("invoice_date", "<=", date_to.isoformat()),
        ]

        # Campos a obtener de Odoo
        fields = [
            "id",
            "partner_id",
            "name",
            "invoice_date",
            "invoice_date_due",
            "amount_total",
            "move_type",
            "state",
            "invoice_payments_widget",
            "currency_id",
        ]

        # Ejecutar consulta a Odoo
        invoices_data = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.move",
                "search_read",
                [domain],
                {"fields": fields},
            ),
        )

        # Recolectar currency_ids únicos para consulta batch
        currency_ids = set()
        for invoice_data in invoices_data:
            raw_currency = invoice_data.get("currency_id")
            if isinstance(raw_currency, list) and len(raw_currency) > 0:
                currency_ids.add(raw_currency[0])
            elif isinstance(raw_currency, int):
                currency_ids.add(raw_currency)

        # Obtener nombres de monedas en una sola consulta
        currencies_map = self._get_currencies_map(list(currency_ids))

        # Transformar datos de Odoo a modelos de dominio
        invoices = []
        for invoice_data in invoices_data:
            # Extraer información del partner (cliente)
            partner_id = 0
            partner_name = ""
            raw_partner = invoice_data.get("partner_id")
            if isinstance(raw_partner, list) and len(raw_partner) > 0:
                partner_id = raw_partner[0]
                partner_name = raw_partner[1]

            # Extraer información de la moneda
            currency_id = None
            currency_name = None
            raw_currency = invoice_data.get("currency_id")
            if isinstance(raw_currency, list) and len(raw_currency) > 0:
                currency_id = raw_currency[0]
                currency_name = currencies_map.get(currency_id, "")
            elif isinstance(raw_currency, int):
                currency_id = raw_currency
                currency_name = currencies_map.get(currency_id, "")

            # Parsear pagos del widget
            payments = self._parse_payment_widget(
                invoice_data.get("invoice_payments_widget")
            )

            invoice = Invoice(
                id=invoice_data.get("id", 0),
                partner_id=partner_id,
                partner_name=partner_name,
                name=invoice_data.get("name", ""),
                invoice_date=invoice_data.get("invoice_date", ""),
                invoice_date_due=invoice_data.get("invoice_date_due"),
                amount_total=invoice_data.get("amount_total", 0.0),
                move_type=invoice_data.get("move_type", ""),
                state=invoice_data.get("state", ""),
                payments=payments,
                currency_id=currency_id,
                currency_name=currency_name,
            )
            invoices.append(invoice)

        return invoices
