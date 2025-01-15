from dataclasses import dataclass
from typing import Optional


@dataclass
class FreshTokenSchema:
    access_token: str
    expires_in: int
    refresh_token: str
    scope: str

@dataclass
class TokenSchema:
    access_token: str
    expires_in: int
    scope: str

@dataclass
class ProfileSchema:
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
