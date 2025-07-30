from typing import Optional
from uuid import UUID

from ninja import ModelSchema, Schema
from pydantic import EmailStr, Field

from accounts.enums import CaseReasonType
from accounts.models import User, CustomerCase, Business
from core.schemas import READ_EXCLUDE_FIELDS


class UserSchema(ModelSchema):
    token: str
    email: EmailStr | None
    has_set_password: bool
    is_social_account: bool
    is_new: bool
    business_role: Optional[str]
    business_user_uid: Optional[UUID]
    phone_number: Optional[str] = None
    phone_code: Optional[str] = None

    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type', 'phone_number', 'phone_code']
    
    @staticmethod
    def resolve_has_set_password(obj):
        return bool(obj.password)

    @staticmethod
    def resolve_business_role(obj):
        if not hasattr(obj, "businessuser"):
            return
        return obj.businessuser.role

    @staticmethod
    def resolve_business_user_uid(obj):
        if not hasattr(obj, "businessuser"):
            return
        return obj.businessuser.uid

    
    @staticmethod
    def resolve_is_social_account(obj):
        return bool(obj.google_id or obj.facebook_id or obj.linkedin_id)
    
    @staticmethod
    def resolve_is_new(obj):
        if hasattr(obj, "__is_new"):
            return True
        return False

class UserListSchema(UserSchema):
    photo_url: Optional[str] = None
    phone_number: Optional[str] = None
    phone_code: Optional[str] = None
    class Meta:
        model = User
        fields = ['uid', 'email', 'first_name', 'last_name', 'type', "phone_number", "phone_code"]

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
    phone_code: Optional[str] = None

class CompanyListSchema(ModelSchema):
    logo: Optional[str] = Field(alias="get_logo")
    class Meta:
        model = Business
        fields = ['uid', 'name']
