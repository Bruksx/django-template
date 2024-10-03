from typing import Optional

from ninja import ModelSchema, Schema
from pydantic import EmailStr

from accounts.models import User, CustomerCase
from core.schemas import READ_EXCLUDE_FIELDS


class UserSchema(ModelSchema):
    token: str
    email: EmailStr | None

    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type']

class UserListSchema(UserSchema):
    photo_url: Optional[str]
    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type']

class RegisterSchema(Schema):
    email: str

class MutateCustomerCaseSchema(ModelSchema):
    class Meta:
        model = CustomerCase
        fields = ("reason", "subject", "description")

class CustomerCaseSchema(ModelSchema):
    user: UserListSchema
    class Meta:
        model = CustomerCase
        exclude = [*READ_EXCLUDE_FIELDS]
