from ninja import Schema, ModelSchema


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

MUTATE_EXCLUDE_FIELDS =  ("id", "created_at", "updated_at", "transaction_id",
                   "uid", "deleted_at", "restored_at")

READ_EXCLUDE_FIELDS = ("transaction_id", "restored_at", "deleted_at")


