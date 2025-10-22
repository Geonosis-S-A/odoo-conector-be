"""Utilidades compartidas para cálculo de precios de empleados."""

from datetime import date
from typing import Dict, List, Optional
from collections import defaultdict

from app.employee_price.domain.models import EmployeePrice


def build_price_index(
    employee_prices: List[EmployeePrice],
) -> Dict[int, List[EmployeePrice]]:
    """
    Construye un índice de precios agrupados por employee_id.

    Args:
        employee_prices: Lista de precios de empleados

    Returns:
        Diccionario con user_id como clave y lista de precios como valor
    """
    index = defaultdict(list)
    for price in employee_prices:
        index[price.user_id].append(price)
    return dict(index)


def get_cost_for_date(
    employee_id: int,
    check_date: date,
    price_index: Dict[int, List[EmployeePrice]],
) -> Optional[float]:
    """
    Obtiene el costo por hora vigente para un empleado en una fecha específica.
    Si no hay precio vigente, retorna el más cercano anterior.
    Si no hay anteriores, retorna el más cercano futuro.

    Args:
        employee_id: ID del empleado
        check_date: Fecha a verificar
        price_index: Índice de precios pre-construido

    Returns:
        Costo por hora si existe un precio vigente o cercano, None si no hay precios
    """
    prices = price_index.get(employee_id, [])

    if not prices:
        return None

    # 1. Primero buscar precio vigente en la fecha exacta
    for price in prices:
        if price.is_active_on(check_date):
            return price.cost_per_hour

    # 2. Si no hay precio vigente, buscar el más cercano anterior
    # Filtrar precios que empezaron antes o en la fecha
    previous_prices = [p for p in prices if p.date_from <= check_date]

    if previous_prices:
        # Ordenar por date_from descendente y tomar el más reciente
        closest = max(previous_prices, key=lambda p: p.date_from)
        return closest.cost_per_hour

    # 3. Si no hay precios anteriores, tomar el más próximo futuro
    future_prices = [p for p in prices if p.date_from > check_date]

    if future_prices:
        # Tomar el que empieza más pronto
        closest = min(future_prices, key=lambda p: p.date_from)
        return closest.cost_per_hour

    return None
