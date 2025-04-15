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


class SocialAuthSchema(BaseModel):
    access_token: str
    social_id: Optional[str]
    user_type: Optional[UserType] = None
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


@dataclass
class Locale:
    country: str
    language: str

@dataclass
class Name:
    localized: Dict[str, str]
    preferredLocale: Locale

@dataclass
class LinkedInProfile:
    localizedFirstName: str
    localizedLastName: str
    firstName: Name
    lastName: Name
    id: str
