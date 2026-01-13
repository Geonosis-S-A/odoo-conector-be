from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any


class SyncRunResponse(BaseModel):
    """Schema de respuesta para el endpoint de sincronización."""
    
    run_id: int = Field(..., description="ID de la ejecución del job")
    status: str = Field(..., description="Estado de la ejecución (success, error, partial_success)")
    message: str = Field(..., description="Mensaje descriptivo del resultado")
    started_at: datetime = Field(..., description="Fecha y hora de inicio de la ejecución")
    finished_at: Optional[datetime] = Field(None, description="Fecha y hora de finalización")
    execution_time_seconds: Optional[float] = Field(None, description="Tiempo de ejecución en segundos")
    new_requests_synced: int = Field(0, description="Cantidad de nuevas solicitudes sincronizadas")
    status_updates_synced: int = Field(0, description="Cantidad de estados actualizados")
    errors_count: int = Field(0, description="Cantidad total de errores")
    run_details: Optional[Dict[str, Any]] = Field(None, description="Detalles completos de la ejecución en formato JSON")

    class Config:
        from_attributes = True
