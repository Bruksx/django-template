from ninja import ModelSchema, Schema
from .models import User, Business


class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name']


class RegisterSchema(Schema):
    email: str
    first_name: str
    last_name: str
    role: str
    company_name: str
    password: str