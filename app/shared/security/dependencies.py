from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.infra.auth_service import JWTPayload, TokenService


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> JWTPayload:
    token = credentials.credentials
    auth_service = TokenService()
    payload = auth_service.verify_token(token)

    return payload
