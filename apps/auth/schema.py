from typing import Optional

from marshmallow.fields import Email
from ninja.schema import BaseModel
from ninja.schema import Field
from ninja import ModelSchema

from apps.accounts.enums import UserType, SocialType
from apps.auth.enums import AuthActionEnum


class LoginSchema(BaseModel):
    email: str
    password: str


class GoogleAuthSchema(BaseModel):
    code: str
    user_type: Optional[UserType] = None


class FaceBookLoginSchema(BaseModel):
    user_id: str
    access_token: str
    type: UserType



