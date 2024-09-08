from dataclasses import dataclass


@dataclass
class TokenDto:
    access_token: str
    refresh_token: str