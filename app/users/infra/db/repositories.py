from app.users.domain.models import User
from app.users.domain.repositories import UserRepository


class SQLModelUserRepository(UserRepository):
    def __init__(self, db):
        self.db = db

    def save_all(self, users: list[User]):
        for user in users:
            self.db.add(user)
        self.db.commit()
