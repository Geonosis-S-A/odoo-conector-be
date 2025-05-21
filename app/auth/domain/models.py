from dataclasses import dataclass


@dataclass
class TokenData:
    user_id: int
    roles: list[str]
