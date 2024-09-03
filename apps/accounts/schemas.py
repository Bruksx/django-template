from ninja import ModelSchema, Schema
from .models import User, Business


class UserSchema(ModelSchema):
    token: str
    
    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type']


class RegisterSchema(Schema):
    email: str


class ValidateOTPSchema(Schema):
    email: str
    otp: str
    first_name: str
    last_name: str
    role: str
    company_name: str
    password: str