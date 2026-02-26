"""
Servicio para consultar feriados de Argentina.
Usa la API https://api.argentinadatos.com/v1/feriados/{year}
con caché en Redis (24 horas).
"""
import json
import requests
from typing import Any

from agent.infra.redis_client import get_redis_client

FERIADOS_API_URL = "https://api.argentinadatos.com/v1/feriados"
CACHE_KEY_PREFIX = "feriados"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 horas


def _get_cache_key(year: int) -> str:
    """Genera la clave de Redis para un año."""
    return f"{CACHE_KEY_PREFIX}:{year}"


def get_feriados_by_year(year: int) -> list[dict[str, Any]]:
    """
    Obtiene los feriados de Argentina para un año.
    Usa cache en Redis si está disponible; si no, consulta la API.

    Args:
        year: Año a consultar (ej: 2025)

    Returns:
        Lista de dicts con {fecha, tipo, nombre}
    """
    redis_client = get_redis_client()
    cache_key = _get_cache_key(year)

    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass  # Si Redis falla, continuar con la API

    try:
        response = requests.get(
            f"{FERIADOS_API_URL}/{year}",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            return []

        # Normalizar formato de fecha a YYYY-MM-DD
        feriados = []
        for item in data:
            if isinstance(item, dict) and "fecha" in item:
                fecha = item.get("fecha", "")
                if "T" in str(fecha):
                    fecha = str(fecha).split("T")[0]
                feriados.append({
                    "fecha": fecha,
                    "tipo": item.get("tipo", ""),
                    "nombre": item.get("nombre", ""),
                })

        try:
            redis_client.setex(
                cache_key,
                CACHE_TTL_SECONDS,
                json.dumps(feriados, ensure_ascii=False),
            )
        except Exception:
            pass  # No fallar si falla el cache

        return feriados

    except requests.RequestException as e:
        raise RuntimeError(f"Error al consultar feriados: {e}") from e


def check_fechas_feriadas(fechas: list[str]) -> list[dict[str, Any]]:
    """
    Verifica cuáles de las fechas indicadas son feriados en Argentina.

    Args:
        fechas: Lista de fechas en formato YYYY-MM-DD

    Returns:
        Lista de dicts con {fecha, nombre} solo para las fechas que son feriado
    """
    if not fechas:
        return []

    # Extraer años únicos
    years = set()
    fechas_normalizadas = []
    for f in fechas:
        if isinstance(f, str) and f.strip():
            fecha_str = f.strip().split("T")[0]
            fechas_normalizadas.append(fecha_str)
            try:
                year = int(fecha_str[:4])
                years.add(year)
            except (ValueError, IndexError):
                pass

    if not years:
        return []

    # Construir mapa fecha -> feriado
    fecha_to_feriado: dict[str, dict] = {}
    for year in years:
        try:
            feriados = get_feriados_by_year(year)
            for fer in feriados:
                fecha = fer.get("fecha", "")
                if "T" in str(fecha):
                    fecha = str(fecha).split("T")[0]
                fecha_to_feriado[fecha] = {
                    "fecha": fecha,
                    "nombre": fer.get("nombre", ""),
                }
        except Exception:
            pass  # Continuar con otros años

    # Filtrar solo las fechas que son feriado
    resultado = []
    for fecha in fechas_normalizadas:
        if fecha in fecha_to_feriado:
            resultado.append(fecha_to_feriado[fecha])

    return resultado
