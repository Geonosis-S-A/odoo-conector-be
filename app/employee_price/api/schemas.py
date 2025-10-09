from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date


class EmployeePriceBase(BaseModel):
    """Schema base para EmployeePrice"""

    user_id: int
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

    cost_per_hour: Optional[float] = Field(default=None, gt=0)
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class EmployeePriceResponse(EmployeePriceBase):
    """Schema de respuesta para un registro de precio de empleado"""

    id: int

    class Config:
        from_attributes = True


class EmployeePriceWithUserResponse(BaseModel):
    """Schema de respuesta para un registro de precio con datos del usuario"""

    id: int
    user_id: int
    email: str
    full_name: str
    date_from: date
    cost_per_hour: Optional[float] = None
    date_to: Optional[date] = None

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
    employee_price: Optional[EmployeePriceWithUserResponse] = None


class CreateEmployeePriceRequest(BaseModel):
    """Schema para crear un nuevo registro de precio de empleado"""

    user_id: int = Field(gt=0, description="ID del usuario/empleado")
    date_from: date = Field(description="Fecha de inicio de vigencia del precio")
    cost_per_hour: Optional[float] = Field(
        default=None, gt=0, description="Costo por hora del empleado (opcional)"
    )
    date_to: Optional[date] = Field(
        default=None, description="Fecha de fin de vigencia (opcional)"
    )


class CreateEmployeePriceResponse(BaseModel):
    """Schema de respuesta para crear un registro de precio de empleado"""

    success: bool
    message: str
    employee_price: Optional[EmployeePriceWithUserResponse] = None


class TeamEmployeePriceItem(BaseModel):
    """Schema para un item de precio de empleado del equipo"""

    employee_id: int
    name: str
    email: str
    cost_per_hour: Optional[float] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ListTeamEmployeePricesResponse(BaseModel):
    """Schema de respuesta para listar precios de empleados del equipo"""

    success: bool
    message: str
    team_members: List[TeamEmployeePriceItem]
    total: int


class EmployeePriceHistoryItem(BaseModel):
    """Schema para un item del historial de precios"""

    id: int
    user_id: int
    date_from: date
    cost_per_hour: Optional[float] = None
    date_to: Optional[date] = None

    class Config:
        from_attributes = True
