from typing import Optional

from accounts.enums import UserType
from ninja.schema import BaseModel


class LoginSchema(BaseModel):
    email: str
    password: str


class GoogleAuthSchema(BaseModel):
    code: str
    user_type: Optional[UserType] = None

class LinkedInAuthSchema(BaseModel):
    code: str
    user_type: Optional[UserType] = None


class FaceBookLoginSchema(BaseModel):
    user_id: str
    access_token: str
    type: UserType



