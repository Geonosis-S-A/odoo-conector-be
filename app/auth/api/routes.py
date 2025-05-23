from typing import Optional
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, Depends, Response, Cookie
from sqlmodel import Session
from app.auth.api.schemas import (
    CreateUserRequest,
    LoginRequest,
    RefreshResponse,
    RegisterResponse,
    TokenResponse,
)
from app.auth.application.use_cases.login import LoginUseCase
from app.auth.application.use_cases.refresh import RefreshUseCase
from app.auth.application.use_cases.register import RegisterUseCase
from app.auth.infra.auth_service import TokenService
from app.auth.infra.db.repositories import (
    SQLModelTokenRepository,
    SQLModelUserCredentialsRepository,
)
from app.shared.infra.db.session import get_db
from app.users.domain.repositories import UserRepository
from app.users.infra.db.repositories import SQLModelUserRepository
from pydantic import BaseModel


router = APIRouter(prefix="/auth", tags=["auth"])


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest, response: Response, db: Session = Depends(get_db)
):
    user_credentials_repository = SQLModelUserCredentialsRepository(db)
    token_repository = SQLModelTokenRepository(db)
    auth_service = TokenService()
    login_use_case = LoginUseCase(
        auth_service, user_credentials_repository, token_repository
    )

    tokens = login_use_case.execute(login_data.email, login_data.password)
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",  # Todo: Restringir al path refresh_token
    )

    return {
        "access_token": tokens.access_token,
        "token_type": "bearer",
        "user": {
            "user_id": tokens.user.user_id,
            "user_email": tokens.user.user_email,
            "user_name": tokens.user.user_name,
            "roles": tokens.user.roles,  # Asegúrate de que los roles están correctamente definidos
        },
    }


@router.post("/register", response_model=RegisterResponse)
def register_user(user: CreateUserRequest, db: Session = Depends(get_db)):
    user_repository = SQLModelUserRepository(db)
    register_user_case = RegisterUseCase(user_repository)
    registered_user = register_user_case.execute(user.email, user.password)
    return RegisterResponse(
        id=registered_user.id,
        email=registered_user.email,
        full_name=registered_user.full_name,
        is_active=registered_user.is_active,
        is_superuser=registered_user.is_superuser,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    token_repository = SQLModelTokenRepository(db)
    user_repository = SQLModelUserCredentialsRepository(db)
    refresh_use_case = RefreshUseCase()
    access_token = refresh_use_case.execute(
        refresh_token, token_repository, user_repository
    )
    return {"access_token": access_token, "token_type": "bearer"}
