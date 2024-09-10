from ninja import ModelSchema, Schema

from accounts.models import User


class UserSchema(ModelSchema):
    token: str
    email: str | None

    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type']

class RegisterSchema(Schema):
    email: str
