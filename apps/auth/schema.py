from typing import Optional

from dataclasses import dataclass
from typing import Dict

from ninja import Schema
from pydantic import EmailStr

from accounts.enums import UserType, SocialType
from ninja.schema import BaseModel

from auth.enums import AuthActionEnum


class LoginSchema(BaseModel):
    email: str
    password: str


class OptionalLoginSchema(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


class SocialAuthSchema(BaseModel):
    access_token: str
    social_id: Optional[str] = None
    user_type: Optional[UserType] = None
    social_type: SocialType
    redirect_uri: Optional[str] = None
    app_id: Optional[str] = None
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""


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


@dataclass
class Locale:
    country: str
    language: str

@dataclass
class LinkedInProfile:
    sub: str
    email_verified: bool
    name: str
    locale: Locale
    given_name: str
    family_name: str
    email: str
    picture: str

@dataclass
class LinkedinOAuthTokenResponse:
    access_token: str
    expires_in: int
    scope: str
    token_type: str
    id_token: str

@dataclass
class FacebookUser:
    id: str
    first_name: str
    last_name: str
    email: str