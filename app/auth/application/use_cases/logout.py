from app.auth.infra.auth_service import TokenService
from app.auth.infra.db.repositories import (
    SQLModelTokenRepository,
)


class LogoutUseCase:
    def __init__(
        self,
        auth_service: TokenService,
        token_repository: SQLModelTokenRepository,
    ):
        self.auth_service = auth_service
        self.token_repository = token_repository

    def execute(self, response, refresh_token):
        return self.auth_service.logout(
            response,
            self.token_repository,
            refresh_token,
        )
