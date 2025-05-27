from abc import ABC, abstractmethod
from typing import Protocol
import bcrypt

class PasswordService(Protocol):
    def hash_password(self, password: str) -> str:
        """Hashea una contraseña usando bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica si una contraseña coincide con su hash"""
        return bcrypt.checkpw(
            plain_password.encode(),
            hashed_password.encode()
        ) 