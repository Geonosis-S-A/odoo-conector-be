from app.users.domain.models import User
from app.users.domain.repositories import UserRepository


class SetPasswordUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, user_id: int, password: str) -> User:
        return self.user_repository.set_password(user_id, password)
