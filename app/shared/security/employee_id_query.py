"""
VT-15 (GEO-1391): parámetro de query ``employee_id`` sólo como entero escalar.

Rechaza HTTP Parameter Pollution: ``employee_id[]``, ``employee_id[0]``, y más de un
valor ``employee_id=...`` en la misma query (comportamiento documentado en el pentest).
"""

from fastapi import HTTPException, Request

_HPP_DETAIL_ARRAY = (
    "No se admite la notación employee_id[] ni variantes indexadas; "
    "use un único parámetro employee_id con un entero."
)


def _reject_employee_id_bracket_keys(request: Request) -> None:
    """Falla si aparecen claves tipo ``employee_id[]`` (no son el escalar ``employee_id``)."""
    for key in request.query_params.keys():
        if key == "employee_id":
            continue
        if key == "employee_id[]" or key.startswith("employee_id["):
            raise HTTPException(status_code=400, detail=_HPP_DETAIL_ARRAY)


def scalar_employee_id_optional(request: Request) -> int | None:
    """
    Devuelve un único ``employee_id`` entero o ``None`` si no se envió el parámetro.

    Raises:
        HTTPException 400: HPP (array/index), duplicado, no entero o <= 0.
    """
    _reject_employee_id_bracket_keys(request)
    raw = request.query_params.getlist("employee_id")
    if len(raw) > 1:
        raise HTTPException(
            status_code=400,
            detail="Parámetro employee_id duplicado",
        )
    if not raw or raw[0] == "":
        return None
    try:
        v = int(raw[0])
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="employee_id debe ser un entero",
        )
    if v <= 0:
        raise HTTPException(status_code=400, detail="employee_id inválido")
    return v
