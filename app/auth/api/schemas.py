from os import access
from typing import Optional
from pydantic import BaseModel
from app.auth.domain.models import TokenData


class CreateUserRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: TokenData


class RegisterResponse(BaseModel):
    id: Optional[int]
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    password: Optional[str] = None


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
