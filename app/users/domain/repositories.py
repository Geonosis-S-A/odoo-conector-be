from abc import ABC, abstractmethod

from app.users.domain.models import Employee, User


class EmployeeGateway(ABC):
    @abstractmethod
    def all(self) -> list[Employee]: ...


class UserRepository(ABC):
    @abstractmethod
    def save_all(self, users: list[User]): ...
