from ninja import Schema


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