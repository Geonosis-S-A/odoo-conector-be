"""Modelos de dominio para el módulo de accounting."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Payment:
    """Representa un pago aplicado a una factura."""

    date: str
    amount: float
    payment_id: Optional[int] = None


@dataclass
class Invoice:
    """Representa una factura de cliente con sus pagos."""

    id: int
    partner_id: int
    partner_name: str
    name: str
    invoice_date: str
    invoice_date_due: Optional[str]
    amount_total: float
    move_type: str
    state: str
    payments: list[Payment]
    currency_id: Optional[int] = None
    currency_name: Optional[str] = None


@dataclass
class ProcessedInvoiceRow:
    """Representa una fila procesada de factura con información de pago."""

    cliente: str
    numero_factura: str
    fecha_factura: str
    fecha_vencimiento: str
    fecha_cobro: str
    monto_factura: float
    monto_cobrado: float
    moneda: str
