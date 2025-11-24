from accounts.models import User, VerificationCode
from accounts.schemas import common as common_schema
from auth.schema import LoginSchema, SocialAuthSchema, ResetPasswordSchema
from auth.services import handle_social_login, validate_login
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from helpers.utils import validate_password
from monkeypatches.response import Response

# Create your views here.
router = Router(tags=["Auth"])


@router.post("login", response=common_schema.UserSchema)
def login(request, data:LoginSchema):
    user = User.objects.filter(email__iexact=data.email).first()
    validate_login(user)
    if not user.check_password(data.password):
        raise HttpError(401, "Invalid login credentials")
    return user


@router.post("social-login", response=common_schema.UserSchema)
@transaction.atomic
def social_auth(request, data: SocialAuthSchema):
    user = handle_social_login(data)
    validate_login(user)
    return user

@router.post("reset-password")
@transaction.atomic
def reset_password(request, data: ResetPasswordSchema):
    validate_password(data.password)
    code = VerificationCode.objects.filter(email__iexact=data.email, code=data.otp).last()
    if not code:
        raise HttpError(400, "Invalid otp")
    if code.expires_at < timezone.now():
        raise HttpError(400, "Otp has expired")
    user = User.objects.filter(email__iexact=data.email).first()
    if not user:
        raise HttpError(404, "No user was found")
    user.set_password(data.password)
    user.save()
    code.hard_delete()
    return Response(data={"message": "password reset successfully"})


@router.get("social-login/redirect")
def social_auth_redirect(request):
    return render(request, "auth/linkedIn_redirect.html")