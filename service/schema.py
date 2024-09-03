from dataclasses import dataclass


@dataclass
class FreshTokenSchema:
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_token_expires: int
    scope: str

@dataclass
class TokenSchema:
    access_token: str
    expires_in: int
    scope: str

@dataclass
class ProfileSchema:
    email: str
    first_name: str
    last_name: str
