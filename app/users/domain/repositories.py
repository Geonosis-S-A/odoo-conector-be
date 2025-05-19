from abc import ABC, abstractmethod

from app.users.domain.models import User


class EmployeeRepository(ABC):
    @abstractmethod
    def all(self) -> list[User]: ...


class UserRepository(ABC):
    @abstractmethod
    def save_all(self, users: list[User]): ...
