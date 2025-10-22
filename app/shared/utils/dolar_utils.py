import requests
from typing import List

BASE_URL = "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD"


def get_cotizacion_promedio_dolar(fecha_desde: str, fecha_hasta: str) -> float:
    """
    Obtiene el promedio de cotización del dólar en un rango de fechas.

    Args:
        fecha_desde: Fecha inicio en formato "YYYY-MM-DD"
        fecha_hasta: Fecha fin en formato "YYYY-MM-DD"

    Returns:
        Promedio de cotización del dólar
    """
    url = f"{BASE_URL}?fechadesde={fecha_desde}&fechahasta={fecha_hasta}"
    response = requests.get(url).json()

    # Obtener todas las cotizaciones en un array plano
    todas_las_cotizaciones: List[float] = []
    for result in response["results"]:
        for detail in result["detalle"]:
            todas_las_cotizaciones.append(detail["tipoCotizacion"])

    # Calcular promedio
    promedio = sum(todas_las_cotizaciones) / len(todas_las_cotizaciones)
    print(promedio)
    return promedio
