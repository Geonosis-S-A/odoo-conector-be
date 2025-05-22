from fastapi import APIRouter, Depends, Response, Cookie, HTTPException
from sqlmodel import Session
from app.auth.api.schemas import LoginRequest, TokenResponse
from app.auth.application.use_cases.login import LoginUseCase
from app.auth.infra.auth_service import TokenService
from app.auth.infra.db.repositories import (
    SQLModelTokenRepository,
    SQLModelUserCredentialsRepository,
)
from app.shared.infra.db.session import get_db
from app.users.infra.db.models import UserModel


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
