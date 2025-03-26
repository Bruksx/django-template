from typing import Optional

from ninja import ModelSchema, Schema
from pydantic import EmailStr

from accounts.enums import CaseReasonType
from accounts.models import User, CustomerCase
from core.schemas import READ_EXCLUDE_FIELDS


class UserSchema(ModelSchema):
    token: str
    email: EmailStr | None

    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type', 'phone_number']

class UserListSchema(UserSchema):
    photo_url: Optional[str]
    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type', "phone_number"]

class RegisterSchema(Schema):
    email: str

class SendEmailOtpSchema(Schema):
    email: EmailStr

class MutateCustomerCaseSchema(ModelSchema):
    reason: CaseReasonType
    class Meta:
        model = CustomerCase
        fields = ("reason", "subject", "description")

class CustomerCaseSchema(ModelSchema):
    user: UserListSchema
    class Meta:
        model = CustomerCase
        exclude = [*READ_EXCLUDE_FIELDS]

class InitiateEmailChangeSchema(Schema):
    email: EmailStr

class ChangeEmailSchema(Schema):
    email: EmailStr
    otp: str

class ChangePasswordSchema(Schema):
    old_password: str
    new_password: str

class ChangePhoneSchema(Schema):
    password: str
    phone_number : str
