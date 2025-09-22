from pydantic import BaseModel


class TimeOffTypeResponse(BaseModel):
    """Schema de respuesta para un tipo de licencia."""
    
    id: int
    name: str
    
    class Config:
        from_attributes = True
