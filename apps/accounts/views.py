from django.core.mail import send_mail
from django.db import transaction
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from accounts.schemas import talent as talent_schemas
from accounts.schemas import common as common_schemas
from accounts.enums import UserType
from accounts.models import User, VerificationCode, Country
from helpers.images import convert_base64_to_image_file

from accounts.models import Talent

router = Router(tags=["Account"])


@router.post("create-account/")
def create_account(request, data: common_schemas.RegisterSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode(email=data.email)
    raw_code = verification_code.save()
    send_mail(
        "OTP",
        f"{raw_code}",
        "from@example.com",
        [data.email],
        fail_silently=False,
    )
    return {
        "message": "verification mail sent!"
    }


@router.post("validate-otp", response={200:common_schemas.UserSchema})
@transaction.atomic
def validate_otp(request, data: talent_schemas.ValidateOTPSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode.objects.filter(email=data.email).last()
    if not verification_code:
        raise HttpError(400, "Incorrect otp")
    request_data = data.__dict__
    is_correct = verification_code.verify_code(data.pop("otp", None))
    if not is_correct:
        raise HttpError(400, "This OTP is invalid")
    user = User.objects.create_user(**request_data.pop("user"),
                               type=UserType.TALENT.value,
                               email_verified=True, is_active=True)
    user.set_password(request_data.pop("password", None))
    user.save()
    country = Country.objects.filter(name__iexact=data.pop("country", None)).first()
    Talent.objects.create(
        user=user,
        country=country,
        **request_data
    )
    return user



@router.patch("complete-profile", response=talent_schemas.MutateTalentSchema, auth=JWTAuth())
def complete_talent_profile(request, data: talent_schemas.MutateTalentSchema):
    talent_user = Talent.objects.filter(user=request.user).first()
    if not talent_user:
        raise HttpError(403, "Not allowed")
    request_data = data.__dict__
    if "user" in data:
        talent_user.user.update(**request_data.pop("user", dict()))
    if "availability" in data:
        talent_user.availability.update(**request_data.pop("availability"))
    if "photo" in data:
        data["photo"] = convert_base64_to_image_file(data["photo"])
    if "cv" in data:
        data["cv"] = convert_base64_to_image_file(data["cv"])
    return talent_user.update(**request_data)
