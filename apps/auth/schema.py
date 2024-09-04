from typing import Optional

from ninja.schema import BaseModel
from ninja.schema import Field

from apps.auth.enums import AuthActionEnum


class LoginSchema(BaseModel):
    email: str
    password: str

class GoogleAuthSchema(BaseModel):
    code: str
    action: Optional[AuthActionEnum] = Field(default="profile")