from ninja import Schema, ModelSchema

from core.models import Currency, Language


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

READ_EXCLUDE_FIELDS = ("id","transaction_id", "restored_at", "deleted_at")

class CurrencySchema(ModelSchema):
    class Meta:
        model = Currency
        fields = ("uid", "name", "abbreviation")

class LanguageSchema(ModelSchema):
    class Meta:
        model = Language
        fields = ("uid", "name")
