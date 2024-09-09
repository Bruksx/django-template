from ninja import ModelSchema, Schema
from accounts.models import User, Business
from jobs.models import EmploymentType


class UserSchema(ModelSchema):
    token: str
    email: str | None
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


class BusinessSchema(ModelSchema):
    class Meta:
        model = Business
        fields = ["size", "description", "website", "industry", "location", "logo", "instagram", "linkedin", "facebook", "twitter_x"]


class EmploymentTypeSchema(ModelSchema):
    #sub_types: list[EmploymentTypeSchema]
    class Meta:
        model = EmploymentType
        fields = ["uid", "name"]