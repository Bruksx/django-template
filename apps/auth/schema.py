from ninja.schema import BaseModel


class LoginSchema(BaseModel):
    email: str
    password: str