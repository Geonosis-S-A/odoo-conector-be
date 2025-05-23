from app.auth.infra.auth_service import TokenService
from app.users.domain.models import User
from app.users.domain.repositories import UserRepository


class RegisterUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.auth_service = TokenService()

    def execute(self, user_email: str, password: str) -> User:
        # TODO: MANDAR MAIL PARA RECONFIGURAR LA CONTRASEÑA
        hashed_password = self.auth_service.hash_password(password)
        return self.user_repository.set_password(user_email, hashed_password)
