from fastapi import HTTPException
from app.auth.domain.repositories import TokenRepository, UserCredentialsRepository
from app.auth.infra.auth_service import TokenService
from app.auth.domain.models import TokenData, RefreshToken
import datetime


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

    async def execute(self, email: str, password: str):
        # TODO: Implementar login

        # 1. Acceder a bbdd y verificar credenciales

        user_credentials = self.user_credentials_repository.get_user_credentials(email)

        # 2. Si credenciales son correctas, crear token. Las credenciales estan hasheadas.
        if not user_credentials:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not self.auth_service.verify_password(user_credentials.password, password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = await self.auth_service.create_access_token(
            TokenData(user_id=user_credentials.id, roles=["user"])
        )

        refresh_token = await self.auth_service.create_refresh_token(
            TokenData(user_id=user_credentials.id, roles=["user"])
        )

        # 3. Guardar refresh token en bbdd
        self.token_repository.save_refresh_token(
            RefreshToken(
                token=refresh_token,
                user_id=user_credentials.id,
            )
        )

        # 4. Devolver access token y refresh token
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
