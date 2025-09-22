from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class TimeOffTypeResponse(BaseModel):
    """Schema de respuesta para un tipo de licencia."""
    
    id: int
    name: str
    
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
        min_length=0
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
                "message": "Solicitud creada exitosamente con ID: 123"
            }
        }
