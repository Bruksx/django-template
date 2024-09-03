from django.shortcuts import render
from ninja import Router
from ninja.errors import HttpError
from .schema import LoginSchema
from accounts.models import User
from accounts.schemas import UserSchema


# Create your views here.
router = Router()


@router.post("login", response=UserSchema)
def login(request, data:LoginSchema):
    user = User.objects.filter(email=data.email).first()
    if user:
        if user.check_password(data.password):
            return user
    raise HttpError(403, "Invalid Credentials")