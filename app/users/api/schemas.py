from pydantic import BaseModel
from typing import Optional, List


class UserBase(BaseModel):
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    roles: Optional[List[int]] = None


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    pass


class UserInDB(UserBase):
    id: int

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True


class UserSyncResponse(BaseModel):
    success: bool
    message: str
    users_created: int
    users_updated: int
    total_processed: int


class SingleUserSyncResponse(BaseModel):
    success: bool
    message: str
    user_updated: bool
    current_data: Optional[dict] = None
    changes_made: Optional[dict] = None


class EmployeeResponse(BaseModel):
    id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True


class EmployeesListResponse(BaseModel):
    success: bool
    message: str
    employees: List[EmployeeResponse]
    total_employees: int


class EmployeePublicResponse(BaseModel):
    """Respuesta reducida para usuarios sin privilegios.

    Expone únicamente el nombre completo (útil para autocomplete en UI).
    Omite email e ID interno para evitar que usuarios básicos puedan
    construir un directorio completo susceptible a password spray (OWASP A07).
    """

    full_name: str


class EmployeesListPublicResponse(BaseModel):
    success: bool
    message: str
    employees: List[EmployeePublicResponse]
    total_employees: int
