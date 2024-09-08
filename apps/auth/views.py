import logging

from django.shortcuts import render
from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Response

from helpers.utils import failure_response, success_response
from .enums import AuthActionEnum
from .schema import LoginSchema, SocialAuthSchema
from services import google
from .services import create_social_user, login_social_user
from accounts.models import User
from accounts.schemas import UserSchema

# Create your views here.
router = Router(tags=["Auth"])


@router.post("login", response=UserSchema)
def login(request, data:LoginSchema):
    user = User.objects.filter(email=data.email).first()
    if user:
        if user.check_password(data.password):
            return user
    raise HttpError(403, "Invalid Credentials")


@router.get("google/login")
def google_login(request):
    return Response(data={"message": "google login successful", "data": google.get_authorization_url()})


@router.post("google/redirect")
def google_redirect(request, data: SocialAuthSchema):
    """
    when google sends the code to the frontend redirect url, they would
    call this end point to create the user and its response may be used to
    continue user profile setup.

    """
    tokens = google.get_tokens(code=data.code)
    if not tokens:
        return failure_response(message= "Tokens not found", status=404)
    profile = google.get_profile_details(tokens.access_token)
    if not profile:
        return failure_response(message="Profile not found", status=404)
    if data.action == AuthActionEnum.LOGIN:
        token = login_social_user(profile, social_type=data.social_type)
        return success_response(message="login is successful", data={"token": token.__dict__})
    elif data.action == AuthActionEnum.SIGNUP:
        token = create_social_user(profile, social_type=data.social_type)
        return success_response(message="login is successful", data={"token": token.__dict__})
    return success_response(message="Profile Details", data=profile.__dict__)
