from typing import Optional

from ninja import Schema, ModelSchema

from accounts.enums import GenderType
from accounts.models import Talent, User

from accounts.models import TalentAvailability

from core.schemas import BASE_EXCLUDE_FIELDS


class ValidateOTPSchema2(Schema):
    email: str
    otp: str
    first_name: str
    last_name: str
    preferred_communication: str
    employment_type: str
    phone_number: str
    country: str
    state: str
    city: str
    postal_code: str
    password: str
    bio: str
    gender: GenderType
    notice_period: str


class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone_number",
                  "gender")

class MutateTalentAvailabilitySchema(ModelSchema):
    class Meta:
        model = TalentAvailability
        exclude = [*BASE_EXCLUDE_FIELDS, "talent"]

"""class MutateTalentSchema(ModelSchema):
    user: Optional[UserSchema]
    availability: Optional[MutateTalentAvailabilitySchema]
    #country: str
    class Meta:
        model = Talent
        exclude = BASE_EXCLUDE_FIELDS"""

class ValidateOTPSchema(Schema):
    otp: str
    password: str
