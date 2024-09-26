from ninja import ModelSchema, Schema
from pydantic import EmailStr

from accounts.models import User


class UserSchema(ModelSchema):
    token: str
    email: EmailStr | None

    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type']

class RegisterSchema(Schema):
    email: str
