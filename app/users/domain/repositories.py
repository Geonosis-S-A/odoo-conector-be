from abc import ABC, abstractmethod
from typing import List

from app.users.domain.models import Employee, User


class EmployeeGateway(ABC):
    @abstractmethod
    def all(self) -> list[Employee]: ...

    @abstractmethod
    def exists_by_id(self, id: int) -> bool: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Employee | None: ...

    @abstractmethod
    def get_user_roles_by_email(self, email: str) -> List[int] | None: ...


class UserRepository(ABC):
    @abstractmethod
    def save_all(self, users: list[User]): ...

    @abstractmethod
    def all(self) -> list[User]: ...

    @abstractmethod
    def set_password(self, user_email: str, password: str) -> User: ...

    @abstractmethod
    def save(self, user: User) -> None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def update_password(self, user_id: int, new_hashed_password: str) -> bool: ...

    @abstractmethod
    def update_user(self, user: User) -> bool: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...
