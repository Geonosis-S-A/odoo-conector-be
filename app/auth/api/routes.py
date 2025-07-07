from typing import Optional
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, Depends, Response, Cookie
from sqlmodel import Session
from app.auth.api.schemas import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    CreateUserRequest,
    LoginRequest,
    RefreshResponse,
    RegisterResponse,
    TokenResponse,
)
from app.auth.application.dto.password_recovery import (
    RequestOTPDTO,
    VerifyOTPDTO,
    ResetPasswordDTO,
)
from app.auth.application.use_cases.exceptions.exceptions import (
    EmployeeNotFound,
    OTPNotFound,
    PasswordNotMatch,
    PasswordUpdateError,
    TokenNotFound,
    UserAlreadyExists,
    UserInactive,
    UserNotFound,
)
from app.auth.application.use_cases.login import LoginUseCase
from app.auth.application.use_cases.logout import LogoutUseCase
from app.auth.application.use_cases.refresh import RefreshUseCase
from app.auth.application.use_cases.register import RegisterUseCase
from app.auth.application.use_cases.change_password import ChangePasswordUseCase
from app.auth.application.use_cases.password_recovery import PasswordRecoveryUseCase
from app.auth.application.use_cases.request_otp_for_register import (
    RequestOTPForRegisterUseCase,
)
from app.auth.infra.auth_service import TokenService
from app.auth.infra.db.repositories import (
    SQLModelOTPRepository,
    SQLModelTokenRepository,
    SQLModelUserCredentialsRepository,
)
from app.shared.infra.db.session import get_db
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.users.infra.db.repositories import SQLModelUserRepository
from pydantic import BaseModel

# Importar las dependencias correctas
from app.auth.api.dependencies import (
    get_email_service,
    get_password_service,
)
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.auth.application.services.crypt_service import BcryptPasswordService


router = APIRouter(prefix="/auth", tags=["auth"])


# Definir la función de dependencia antes de los endpoints que la usan
def get_password_recovery_use_case(
    email_service=Depends(get_email_service),
    password_service=Depends(get_password_service),
    db: Session = Depends(get_db),
) -> PasswordRecoveryUseCase:
    return PasswordRecoveryUseCase(
        user_repository=SQLModelUserRepository(db),
        email_service=email_service,
        password_service=password_service,
        otp_repository=SQLModelOTPRepository(db),
    )


def get_request_otp_for_register_use_case(
    db: Session = Depends(get_db),
    email_service=Depends(get_email_service),
    odoo_client=Depends(get_odoo_connection),
) -> RequestOTPForRegisterUseCase:
    return RequestOTPForRegisterUseCase(
        user_repository=SQLModelUserRepository(db),
        email_service=email_service,
        otp_repository=SQLModelOTPRepository(db),
        employee_gateway=OdooEmployeeGateway(odoo_client),
    )


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
    try:
        tokens = login_use_case.execute(login_data.email, login_data.password)
    except UserNotFound as e:
        raise HTTPException(status_code=401, detail=str(e))
    except PasswordNotMatch as e:
        raise HTTPException(status_code=401, detail=str(e))
    except UserInactive as e:
        raise HTTPException(status_code=401, detail=str(e))
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",  # Todo: Restringir al path refresh_token
        max_age=30 * 24 * 60 * 60,  # Todo: corregir hardcodeada
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
    # Todo manejar excepciones acá. El endpoint eesta en desuso por ahora
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


@router.post("/logout")
async def logout(
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    refresh_token: Optional[str] = Cookie(default=None),
):
    auth_service = TokenService()
    token_repository = SQLModelTokenRepository(db)
    logout_use_case = LogoutUseCase(auth_service, token_repository)
    try:
        logout_use_case.execute(response, refresh_token)
    except TokenNotFound as e:
        raise HTTPException(status_code=401, detail=str(e))
    return {"message": "Successfully logged out"}


@router.put("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cambia la contraseña de un usuario."""
    user_credentials_repository = SQLModelUserCredentialsRepository(db)
    password_service = BcryptPasswordService()
    change_password_use_case = ChangePasswordUseCase(
        password_service, user_credentials_repository
    )

    try:
        # Obtener user_id del token en lugar del body
        user_id = current_user["user_id"]

        change_password_use_case.execute(
            user_id, request.current_password, request.new_password
        )
        return ChangePasswordResponse(message="Contraseña cambiada exitosamente")
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UserInactive as e:
        raise HTTPException(status_code=401, detail=str(e))
    except PasswordNotMatch as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PasswordUpdateError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/password-recovery/request")
async def request_otp(
    dto: RequestOTPDTO,
    password_recovery_use_case: PasswordRecoveryUseCase = Depends(
        get_password_recovery_use_case
    ),
):
    try:
        await password_recovery_use_case.request_otp(dto)
        return {"message": "OTP sent successfully"}
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail="User not found")
    except OTPNotFound as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/register/request-otp")
async def request_otp_for_register(
    dto: RequestOTPDTO,
    request_otp_for_register_use_case: RequestOTPForRegisterUseCase = Depends(
        get_request_otp_for_register_use_case
    ),
):
    try:
        await request_otp_for_register_use_case.execute(dto.email)
        return {"message": "OTP sent successfully"}
    except EmployeeNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UserAlreadyExists as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al enviar OTP")


@router.post("/password-recovery/verify")
async def verify_otp(
    dto: VerifyOTPDTO,
    password_recovery_use_case: PasswordRecoveryUseCase = Depends(
        get_password_recovery_use_case
    ),
):
    try:
        await password_recovery_use_case.verify_otp(dto)
        return {"message": "OTP verified successfully"}
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail="User not found")
    except OTPNotFound as e:
        raise HTTPException(status_code=400, detail="Invalid OTP")


@router.post("/password-recovery/reset")
async def reset_password(
    dto: ResetPasswordDTO,
    password_recovery_use_case: PasswordRecoveryUseCase = Depends(
        get_password_recovery_use_case
    ),
):
    try:
        await password_recovery_use_case.reset_password(dto)
        return {"message": "Password reset successfully"}
    except PasswordNotMatch as e:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    except OTPNotFound as e:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail="User not found")
