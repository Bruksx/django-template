from uuid import UUID

from ninja import Schema, ModelSchema
from pydantic import condecimal
from core.models import Currency, Language

from accounts.models import Country, EducationLevel



class ErrorDetail(Schema):
    type: str
    loc: list[str]
    msg: str

class FieldErrorSchema(Schema):
    detail: list[ErrorDetail]


class StringDetailSchema(Schema):
    detail: str


class MessageSchema(Schema):
    message: str


class StringSchema(Schema):
    pass

MUTATE_EXCLUDE_FIELDS =  ("id", "created_at", "updated_at", "transaction_id", "deleted_at", "restored_at")

READ_EXCLUDE_FIELDS = ("id", "transaction_id", "restored_at", "deleted_at")

class CurrencySchema(ModelSchema):
    class Meta:
        model = Currency
        fields = ("uid", "name", "abbreviation")

class LanguageSchema(ModelSchema):
    class Meta:
        model = Language
        fields = ("uid", "name")

class CountrySchema(ModelSchema):
    class Meta:
        model = Country
        fields = ("uid", "name", "code")

class EducationLevelSchema(ModelSchema):
    industry: str
    class Meta:
        model = EducationLevel
        fields = ("uid", "industry", "level")

    @staticmethod
    def resolve_industry(obj):
        return obj.industry.name


class GenericNameAndUidSchema(Schema):
    uid: UUID
    name: str



DecimalType = condecimal(max_digits=12, decimal_places=2)


class UserMiniSchema(Schema):
    uid: UUID
    first_name: str
    last_name: str
    email: str