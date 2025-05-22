from abc import ABC, abstractmethod

from app.users.domain.models import Employee, User


class EmployeeGateway(ABC):
    @abstractmethod
    def all(self) -> list[Employee]: ...


class UserRepository(ABC):
    @abstractmethod
    def save_all(self, users: list[User]): ...

    @abstractmethod
    def all(self) -> list[User]: ...

    @abstractmethod
    def set_password(self, user_email: str, password: str) -> User: ...
