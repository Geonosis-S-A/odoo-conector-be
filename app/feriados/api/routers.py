from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from agent.services.feriados_service import get_feriados_by_year
from app.shared.security.dependencies import get_current_user

router = APIRouter(prefix="/feriados", tags=["feriados"])


class FeriadoResponse(BaseModel):
    fecha: str  # YYYY-MM-DD
    tipo: str
    nombre: str


@router.get("", response_model=List[FeriadoResponse])
def listar_feriados(
    year: int = Query(..., ge=2000, le=2100),
    _user=Depends(get_current_user),
):
    """Feriados de Argentina del año (API pública + FERIADOS_EXTRA)."""
    try:
        feriados = get_feriados_by_year(year)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return sorted(feriados, key=lambda f: f["fecha"])
