from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    pass


class UserInDB(UserBase):
    id: int

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    pass
