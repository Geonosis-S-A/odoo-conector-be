from fastapi import HTTPException
from app.auth.application.use_cases.exceptions.exceptions import (
    TokenNotFound,
    TokenRevoked,
    UserNotFound,
)
from app.auth.infra.auth_service import TokenService
from app.auth.infra.db.repositories import (
    SQLModelTokenRepository,
    SQLModelUserCredentialsRepository,
)


class RefreshUseCase:
    def __init__(self):
        self.auth_service = TokenService()

    def execute(
        self,
        refresh_token: str,
        token_repository: SQLModelTokenRepository,
        user_repository: SQLModelUserCredentialsRepository,
    ) -> str:
        try:
            return self.auth_service.refresh_access_token(
                refresh_token, token_repository, user_repository
            )
        except TokenNotFound as e:
            raise HTTPException(status_code=401, detail=str(e))
        except TokenRevoked as e:
            raise HTTPException(status_code=401, detail=str(e))
        except UserNotFound as e:
            raise HTTPException(status_code=401, detail=str(e))
