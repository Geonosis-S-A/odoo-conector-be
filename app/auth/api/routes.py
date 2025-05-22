from atexit import register
import email
from http.client import HTTPException
from http.cookiejar import Cookie
from fastapi import APIRouter, Depends, Response
from sqlmodel import Session
from app.auth.api.schemas import (
    CreateUserRequest,
    LoginRequest,
    RegisterResponse,
    TokenResponse,
)
from app.auth.application.use_cases.login import LoginUseCase
from app.auth.application.use_cases.register import RegisterUseCase
from app.auth.infra.auth_service import TokenService
from app.auth.infra.db.repositories import (
    SQLModelTokenRepository,
    SQLModelUserCredentialsRepository,
)
from app.shared.infra.db.session import get_db
from app.users.domain.repositories import UserRepository
from app.users.infra.db.repositories import SQLModelUserRepository


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest, response: Response, db: Session = Depends(get_db)
):
    print(f"Sesión de base de datos: {db}")

    user_credentials_repository = SQLModelUserCredentialsRepository(db)
    token_repository = SQLModelTokenRepository(db)
    auth_service = TokenService()
    login_use_case = LoginUseCase(
        auth_service, user_credentials_repository, token_repository
    )

    tokens = await login_use_case.execute(login_data.email, login_data.password)
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


@router.post("/register")
def register_user(
    user: CreateUserRequest, db: Session = Depends(get_db)
) -> RegisterResponse:
    user_repository = SQLModelUserRepository(db)
    auth_service = TokenService()
    register_user_case = RegisterUseCase(user_repository, auth_service)
    registered_user = register_user_case.execute(user.email, user.password)
    return RegisterResponse(
        id=registered_user.id,
        email=registered_user.email,
        full_name=registered_user.full_name,
        is_active=registered_user.is_active,
        is_superuser=registered_user.is_superuser,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str = Cookie(None, alias="refresh_token"),
    session: Session = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    
    auth_service = TokenService(session)
    return auth_service.refresh_access_token(refresh_token)
