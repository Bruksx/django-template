from django.db import transaction
from django.utils import timezone
from ninja.responses import Response

from accounts.models import User, VerificationCode
from accounts.schemas import common as common_schema
from ninja import Router
from ninja.errors import HttpError

from auth.enums import AuthActionEnum
from helpers.utils import validate_password
from services.auth.schema import ProfileSchema
from auth.schema import LoginSchema, SocialAuthSchema, ResetPasswordSchema
from auth.services import handle_social_login, validate_login

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
    profile = ProfileSchema(id=data.social_id, email=data.email, first_name=data.first_name, last_name=data.last_name)
    if data.email is None or data.first_name is None or data.last_name is None:
        action = AuthActionEnum.LOGIN
    else:
        action = AuthActionEnum.SIGNUP
    user = handle_social_login(profile, data.user_type, data.social_type, action)
    validate_login(user)
    return user

@router.post("reset-password")
@transaction.atomic
def reset_password(request, data: ResetPasswordSchema):
    validate_password(data.password)
    code = VerificationCode.objects.filter(email=data.email, code=data.otp).first()
    if not code:
        raise HttpError(400, "Invalid otp")
    if code.expires_at < timezone.now():
        raise HttpError(400, "Otp has expired")
    user = User.objects.filter(email__iexact=data.email).first()
    if not user:
        raise HttpError(404, "No user was found")
    user.set_password(data.password)
    user.save()
    code.delete()
    return Response(data={"message": "password reset successfully"})
