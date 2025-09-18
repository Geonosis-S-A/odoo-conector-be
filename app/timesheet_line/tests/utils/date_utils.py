"""
Utilidades para manejo de fechas en tests de timesheet.
Evita usar fechas hardcodeadas que pueden fallar cuando Odoo valida períodos.
"""

from datetime import date, timedelta
from typing import List


def get_valid_test_date(days_from_today: int = 7) -> str:
    """
    Obtiene una fecha válida para tests, evitando fechas que puedan estar validadas en Odoo.
    
    Args:
        days_from_today: Número de días desde hoy (por defecto 7 días en el futuro)
        
    Returns:
        str: Fecha en formato YYYY-MM-DD
    """
    test_date = date.today() + timedelta(days=days_from_today)
    return test_date.strftime("%Y-%m-%d")


def get_valid_date_range(start_days_from_today: int = 7, end_days_from_today: int = 30) -> tuple[str, str]:
    """
    Obtiene un rango de fechas válido para tests.
    
    Args:
        start_days_from_today: Días desde hoy para la fecha de inicio
        end_days_from_today: Días desde hoy para la fecha de fin
        
    Returns:
        tuple[str, str]: Tupla con fecha_inicio y fecha_fin en formato YYYY-MM-DD
    """
    start_date = date.today() + timedelta(days=start_days_from_today)
    end_date = date.today() + timedelta(days=end_days_from_today)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def get_multiple_test_dates(count: int = 3, start_days_from_today: int = 7) -> List[str]:
    """
    Obtiene múltiples fechas válidas para tests, espaciadas por días.
    
    Args:
        count: Número de fechas a generar
        start_days_from_today: Días desde hoy para empezar
        
    Returns:
        List[str]: Lista de fechas en formato YYYY-MM-DD
    """
    dates = []
    for i in range(count):
        test_date = date.today() + timedelta(days=start_days_from_today + i)
        dates.append(test_date.strftime("%Y-%m-%d"))
    return dates


def get_date_range_for_filtering(days_margin: int = 5) -> tuple[str, str]:
    """
    Obtiene un rango de fechas amplio para filtros en tests.
    
    Args:
        days_margin: Margen de días alrededor de las fechas de test
        
    Returns:
        tuple[str, str]: Tupla con fecha_inicio y fecha_fin para filtros
    """
    start_date = date.today() + timedelta(days=days_margin)
    end_date = date.today() + timedelta(days=60)  # Rango amplio para tests
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def get_wide_date_range_for_filtering() -> tuple[str, str]:
    """
    Obtiene un rango muy amplio de fechas para filtros que necesitan capturar tests.
    La fecha de inicio es anterior a las fechas de test típicas.
    
    Returns:
        tuple[str, str]: Tupla con fecha_inicio y fecha_fin muy amplios
    """
    start_date = date.today() + timedelta(days=1)  # Fecha anterior a las fechas de test
    end_date = date.today() + timedelta(days=60)   # Rango amplio para tests
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
