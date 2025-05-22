from pydantic import BaseModel
from app.auth.domain.models import TokenData


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: TokenData
