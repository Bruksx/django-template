from typing import Optional

from accounts.enums import UserType
from ninja.schema import BaseModel

from auth.enums import AuthActionEnum


class LoginSchema(BaseModel):
    email: str
    password: str


class GoogleAuthSchema(BaseModel):
    code: str
    user_type: Optional[UserType] = None
    action: AuthActionEnum

class LinkedInAuthSchema(BaseModel):
    code: str
    user_type: Optional[UserType] = None
    action: AuthActionEnum


class FaceBookLoginSchema(BaseModel):
    user_id: str
    access_token: str
    type: UserType
    action: AuthActionEnum




