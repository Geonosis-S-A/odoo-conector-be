from fastapi import HTTPException
from app.auth.application.dto.login_response_dto import LoginResponse
from app.auth.domain.repositories import TokenRepository, UserCredentialsRepository
from app.auth.infra.auth_service import TokenService
from app.auth.domain.models import TokenData, RefreshToken


class LoginUseCase:
    def __init__(
        self,
        auth_service: TokenService,
        user_credentials_repository: UserCredentialsRepository,
        token_repository: TokenRepository,
    ):
        self.auth_service = auth_service
        self.user_credentials_repository = user_credentials_repository
        self.token_repository = token_repository

    async def execute(self, email: str, password: str) -> LoginResponse:
        # 1. Acceder a bbdd y verificar credenciales
        user_credentials = self.user_credentials_repository.get_user_credentials(email)

        # 2. Si credenciales son correctas, crear token. Las credenciales estan hasheadas.
        if not user_credentials:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not self.auth_service.verify_password(user_credentials.password, password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not self.auth_service.is_active(user_credentials.is_active):
            raise HTTPException(status_code=401, detail="Inactive user")

        access_token = await self.auth_service.create_access_token(
            TokenData(
                user_id=user_credentials.id,
                user_email=user_credentials.email,
                user_name=user_credentials.name,
                roles=["user"],
            )
        )

        refresh_token = await self.auth_service.create_refresh_token(
            TokenData(
                user_id=user_credentials.id,
                user_email=user_credentials.email,
                user_name=user_credentials.name,
                roles=["user"],
            )
        )

        # 3. Guardar refresh token en bbdd
        self.token_repository.save_refresh_token(
            RefreshToken(
                token=refresh_token,
                user_id=user_credentials.id,
            )
        )

        print(user_credentials.id)
        print(user_credentials.name)
        print(user_credentials.email)

        # 4. Devolver access token y detalles del usuario
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=TokenData(
                user_id=user_credentials.id,
                user_name=user_credentials.name,
                user_email=user_credentials.email,
                roles=["user"],
            ),
        )
