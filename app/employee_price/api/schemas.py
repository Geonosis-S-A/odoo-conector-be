from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date


class EmployeePriceBase(BaseModel):
    """Schema base para EmployeePrice"""

    user_id: int
    email: str
    full_name: str
    date_from: date
    cost_per_hour: Optional[float] = Field(
        default=None, gt=0, description="Costo por hora del empleado"
    )
    date_to: Optional[date] = None


class EmployeePriceCreate(EmployeePriceBase):
    """Schema para crear un nuevo registro de precio de empleado"""

    pass


class EmployeePriceUpdate(BaseModel):
    """Schema para actualizar un registro de precio de empleado"""

    email: Optional[str] = None
    full_name: Optional[str] = None
    cost_per_hour: Optional[float] = Field(default=None, gt=0)
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class EmployeePriceResponse(EmployeePriceBase):
    """Schema de respuesta para un registro de precio de empleado"""

    id: int

    class Config:
        from_attributes = True


class EmployeePriceListResponse(BaseModel):
    """Schema de respuesta para lista de precios de empleados"""

    success: bool
    message: str
    employee_prices: List[EmployeePriceResponse]
    total: int


class SyncUsersToEmployeePriceResponse(BaseModel):
    """Schema de respuesta para la sincronización de usuarios a employee_price"""

    success: bool
    message: str
    total_users: int
    synced_count: int
    skipped_count: int
    failed_count: int
    details: Optional[Dict[str, Any]] = None


class UserSyncDetail(BaseModel):
    """Detalle de un usuario sincronizado"""

    id: Optional[int] = None
    user_id: int
    email: str
    full_name: str


class SkippedUserDetail(BaseModel):
    """Detalle de un usuario omitido"""

    user_id: int
    email: str
    reason: str


class FailedUserDetail(BaseModel):
    """Detalle de un usuario fallido"""

    user_id: int
    email: str
    error: str


class SetCostPerHourRequest(BaseModel):
    """Schema para actualizar el costo por hora"""

    cost_per_hour: float = Field(gt=0, description="Costo por hora del empleado")


class SetCostPerHourResponse(BaseModel):
    """Schema de respuesta para actualizar el costo por hora"""

    success: bool
    message: str
    employee_price: Optional[EmployeePriceResponse] = None

