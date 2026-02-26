"""
Herramientas del agente para consultar feriados en Argentina.
"""
import json
from datetime import datetime
from langchain.tools import tool

from agent.services.feriados_service import check_fechas_feriadas


def _normalize_date_to_iso(date_str: str) -> str | None:
    """Normaliza una fecha a formato YYYY-MM-DD."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    if not date_str:
        return None
    # Quitar parte de tiempo si existe
    if "T" in date_str:
        date_str = date_str.split("T")[0]
    # YYYY-MM-DD
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        pass
    # DD/MM/YYYY
    try:
        parsed = datetime.strptime(date_str, "%d/%m/%Y")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        pass
    return None


@tool
def check_feriados_argentina(dates_json: str) -> str:
    """Verifica si las fechas indicadas son feriados en Argentina.

    Usa esta herramienta ANTES de crear entradas de timesheet para validar
    que las fechas no sean feriados. Si alguna fecha es feriado y el usuario
    no indicó explícitamente que quiere cargar en feriado, descartá esas
    entradas e informá al usuario.

    Args:
        dates_json: JSON string con array de fechas. Formatos aceptados:
                    YYYY-MM-DD (ej: "2025-05-25") o DD/MM/YYYY.
                    Ejemplo: '["2025-05-25", "2025-12-25"]'

    Returns:
        JSON string con:
        - feriados: lista de {fecha, nombre} para las fechas que son feriado.
        - Si ninguna es feriado, feriados será lista vacía.
        - Si hay error al verificar, feriados será [] y puede incluir "error".
    """
    try:
        data = json.loads(dates_json)
    except json.JSONDecodeError as e:
        return json.dumps(
            {
                "success": False,
                "error": "JSON inválido",
                "message": str(e),
                "feriados": [],
            },
            ensure_ascii=False,
        )

    if not isinstance(data, list):
        return json.dumps(
            {
                "success": False,
                "error": "El JSON debe ser un array de fechas",
                "feriados": [],
            },
            ensure_ascii=False,
        )

    fechas_normalizadas = []
    for item in data:
        if isinstance(item, str):
            normalized = _normalize_date_to_iso(item)
            if normalized:
                fechas_normalizadas.append(normalized)
        elif isinstance(item, (int, float)):
            # Por si viene como timestamp o número
            continue

    if not fechas_normalizadas:
        return json.dumps(
            {
                "success": True,
                "feriados": [],
                "message": "No se pudieron parsear fechas válidas",
            },
            ensure_ascii=False,
        )

    try:
        feriados = check_fechas_feriadas(fechas_normalizadas)
        return json.dumps(
            {
                "success": True,
                "feriados": feriados,
                "total_consultadas": len(fechas_normalizadas),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": str(e),
                "feriados": [],
                "message": "No se pudo verificar feriados. Procedé con la carga si tenés los datos necesarios.",
            },
            ensure_ascii=False,
        )
