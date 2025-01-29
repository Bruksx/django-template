from typing import Optional

from ninja import Schema
from pydantic import EmailStr

from accounts.enums import UserType, SocialType
from ninja.schema import BaseModel

from auth.enums import AuthActionEnum


class LoginSchema(BaseModel):
    email: str
    password: str


class SocialAuthSchema(BaseModel):
    social_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    user_type: UserType
    social_type: SocialType


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

class ResetPasswordSchema(Schema):
    email: EmailStr
    otp: str
    password: str




