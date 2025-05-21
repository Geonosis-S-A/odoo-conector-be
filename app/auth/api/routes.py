from fastapi import APIRouter, Depends, Response, Cookie, HTTPException
from sqlmodel import Session
from app.auth.api.schemas import LoginRequest, TokenResponse
from app.auth.application.use_cases.login import LoginUseCase
from app.auth.infra.auth_service import TokenService


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
):
    user_service = TokenService()
    return await user_service.login(login_data.email, login_data.password)
