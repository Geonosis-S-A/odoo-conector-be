"""Interfaces (Gateways) para el módulo de accounting."""

from abc import ABC, abstractmethod
from datetime import date
from typing import List
from app.accounting.domain.models import Invoice


class AccountingGateway(ABC):
    """Gateway para operaciones de contabilidad en Odoo."""

    @abstractmethod
    def get_customer_invoices(
        self,
        date_from: date,
        date_to: date,
    ) -> List[Invoice]:
        """
        Obtiene facturas de clientes posteadas en un rango de fechas.

        Args:
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período

        Returns:
            Lista de facturas con información de pagos
        """
        ...
