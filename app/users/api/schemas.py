from pydantic import BaseModel, EmailStr
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
