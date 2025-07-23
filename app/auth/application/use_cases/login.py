from fastapi import HTTPException
from app.auth.application.dto.login_response_dto import LoginResponse
from app.auth.application.services.crypt_service import BcryptPasswordService
from app.auth.application.use_cases.exceptions.exceptions import (
    PasswordNotMatch,
    UserInactive,
    UserNotFound,
)
from app.auth.domain.repositories import TokenRepository, UserCredentialsRepository
from app.auth.infra.auth_service import TokenService
from app.auth.domain.models import TokenData, RefreshToken


class LoginUseCase:
    def __init__(
        self,
        token_service: TokenService,
        user_credentials_repository: UserCredentialsRepository,
        token_repository: TokenRepository,
        password_service: BcryptPasswordService = BcryptPasswordService(),
    ):
        self.token_service = token_service
        self.user_credentials_repository = user_credentials_repository
        self.token_repository = token_repository
        self.password_service = password_service

    def execute(self, email: str, password: str) -> LoginResponse:
        # 1. Acceder a bbdd y verificar credenciales
        user_credentials = self.user_credentials_repository.get_user_credentials(email)

        # 2. Si credenciales son correctas, crear token. Las credenciales estan hasheadas.
        if not user_credentials:
            raise UserNotFound("User not found")

        if not self.password_service.verify_password(
            password, user_credentials.password
        ):
            raise PasswordNotMatch("Invalid credentials")

        if not user_credentials.is_active:
            raise UserInactive("Inactive user")

        # Usar los roles reales del usuario o una lista vacía si no tiene roles
        user_roles = user_credentials.roles or []

        access_token = self.token_service.create_access_token(
            TokenData(
                user_id=user_credentials.id,
                user_email=user_credentials.email,
                user_name=user_credentials.name,
                roles=user_roles,
            )
        )

        refresh_token = self.token_service.create_refresh_token(
            TokenData(
                user_id=user_credentials.id,
                user_email=user_credentials.email,
                user_name=user_credentials.name,
                roles=user_roles,
            )
        )

        # 3. Guardar refresh token en bbdd. Estoy asumiendo que va a andar bien, podría mejorarse
        self.token_repository.save_refresh_token(
            RefreshToken(
                token=refresh_token,
                user_id=user_credentials.id,
            )
        )

        # 4. Devolver access token y detalles del usuario
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=TokenData(
                user_id=user_credentials.id,
                user_name=user_credentials.name,
                user_email=user_credentials.email,
                roles=user_roles,
            ),
        )
