from dataclasses import dataclass


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
    email: str
    first_name: str
    last_name: str
