from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any


class TimeOffTypeResponse(BaseModel):
    """Schema de respuesta para un tipo de licencia."""

    id: int
    name: str
    virtual_remaining_leaves: float
    requires_allocation: bool
    has_valid_allocation: bool
    allows_negative: bool

    class Config:
        from_attributes = True


class TimeOffRequestCreate(BaseModel):
    """Schema para crear una nueva solicitud de tiempo personal."""

    holiday_status_id: int = Field(..., description="ID del tipo de licencia", gt=0)
    request_date_from: date = Field(..., description="Fecha de inicio de la licencia")
    request_date_to: date = Field(..., description="Fecha de fin de la licencia")
    description: Optional[str] = Field(
        default=None,
        description="Descripción/motivo de la solicitud (opcional)",
        max_length=500,
        min_length=0,
    )

    class Config:
        from_attributes = True


class TimeOffRequestUpdate(BaseModel):
    """Schema para actualizar una solicitud de tiempo personal existente."""

    holiday_status_id: int = Field(..., description="ID del tipo de licencia", gt=0)
    request_date_from: date = Field(..., description="Fecha de inicio de la licencia")
    request_date_to: date = Field(..., description="Fecha de fin de la licencia")
    description: Optional[str] = Field(
        default=None,
        description="Descripción/motivo de la solicitud (opcional)",
        max_length=500,
        min_length=0,
    )

    class Config:
        from_attributes = True


class TimeOffRequestResponse(BaseModel):
    """Schema de respuesta para una solicitud de tiempo personal creada."""

    request_id: Optional[int] = Field(None, description="ID de la solicitud creada")
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo del resultado")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "request_id": 123,
                "success": True,
                "message": "Solicitud creada exitosamente con ID: 123",
            }
        }


class TimeOffRequestInfoResponse(BaseModel):
    """Schema de respuesta para información de una solicitud de tiempo personal existente."""

    id: int = Field(..., description="ID de la solicitud")
    holiday_status_id: int = Field(..., description="ID del tipo de licencia")
    holiday_status_name: str = Field(..., description="Nombre del tipo de licencia")
    name: Optional[str] = Field(None, description="Descripción/motivo de la solicitud")
    request_date_from: date = Field(..., description="Fecha de inicio de la licencia")
    request_date_to: date = Field(..., description="Fecha de fin de la licencia")
    employee_id: int = Field(..., description="ID del empleado")
    employee_name: str = Field(..., description="Nombre del empleado")
    state: str = Field(..., description="Estado de la solicitud")
    number_of_days: float = Field(..., description="Número de días de la solicitud")

    class Config:
        from_attributes = True


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
