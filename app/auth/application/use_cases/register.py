from app.auth.application.services.crypt_service import BcryptPasswordService
from app.users.domain.models import User
from app.users.domain.repositories import UserRepository


class RegisterUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.password_service = BcryptPasswordService()

    def execute(self, user_email: str, password: str) -> User:
        hashed_password = self.password_service.hash_password(password)
        return self.user_repository.set_password(user_email, hashed_password)
