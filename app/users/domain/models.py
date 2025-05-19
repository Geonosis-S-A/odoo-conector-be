# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Domain User entity, decoupled from ORM"""

    id: Optional[int]
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool

    @classmethod
    def from_request(
        cls,
        email: str,
        full_name: str,
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> "User":
        """Create a new user from request data"""
        return cls(
            id=None,
            email=email,
            full_name=full_name,
            is_active=is_active,
            is_superuser=is_superuser,
        )
