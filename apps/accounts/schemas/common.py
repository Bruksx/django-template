from ninja import ModelSchema, Schema
from pydantic import EmailStr

from accounts.models import User, CustomerCase


class UserSchema(ModelSchema):
    token: str
    email: EmailStr | None

    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type']

class UserListSchema(UserSchema):
    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type']

class RegisterSchema(Schema):
    email: str

class CreateCustomerCaseSchema(Schema):
    class Meta:
        model = CustomerCase
        fields = ("reason", "subject", "description")
