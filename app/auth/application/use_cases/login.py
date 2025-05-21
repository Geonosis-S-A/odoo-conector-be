from app.auth.infra.auth_service import TokenService
from app.auth.domain.models import TokenData


class LoginUseCase:
    def __init__(self, auth_service: TokenService):
        self.auth_service = auth_service

    async def execute(self, email: str, password: str) -> TokenData:
        return await self.auth_service.login(email, password)
