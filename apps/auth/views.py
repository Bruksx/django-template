import logging

from django.shortcuts import render
from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Response

from .schema import LoginSchema
from accounts.models import User
from accounts.schemas import UserSchema
from services import google

# Create your views here.
router = Router()


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


@router.get("google/redirect")
def google_redirect(request):
    code = request.GET.get("code")
    tokens = google.get_tokens(code=code)
    if not tokens:
        return Response(data={"message": "Tokens not found"}, status=404)
    profile = google.get_profile_details(tokens.access_token)
    if not profile:
        return Response(data={"message": "Profile not found"}, status=404)
    #TODO: the profile would be used to create the user with a verified email account.
    return Response(data={"message": "Profile details", "data": profile.__dict__})