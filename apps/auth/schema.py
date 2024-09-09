from typing import Optional

from ninja.schema import BaseModel
from ninja.schema import Field
from ninja import ModelSchema

from apps.accounts.enums import UserType, SocialType
from apps.auth.enums import AuthActionEnum


class LoginSchema(BaseModel):
    email: str
    password: str


class SocialAuthSchema(BaseModel):
    code: str
    action: Optional[AuthActionEnum] = None
    user_type: Optional[UserType] = None
    social_type: SocialType


class FaceBookLoginSchema(BaseModel):
    user_id: str
    access_token: str
    type: UserType