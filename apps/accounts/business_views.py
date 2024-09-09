from ninja import Router, Schema
from . import schemas
from accounts.models import User, Business, BusinessUser, VerificationCode
from django.core.mail import send_mail
from django.db import transaction
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from .enums import UserType
from helpers.images import convert_base64_to_image_file
from typing import List


router = Router(tags=["Business Account"])


@router.post("create-account/")
def create_account(request, data: schemas.RegisterSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account withn this email already exists")
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


@router.post("validate-otp", response={200:schemas.UserSchema})
@transaction.atomic
def validate_otp(request, data: schemas.ValidateOTPSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account withn this email already exists")
    verification_code = VerificationCode.objects.filter(email=data.email).last()
    if verification_code:
        is_correct = verification_code.verify_code(data.otp)
        if is_correct:
            user = User.objects.create(
                role=data.role,
                first_name=data.first_name,
                last_name=data.last_name,
                type=UserType.BUSINESS.value,
                email=data.email,
                username=None,
                email_verified=True,
            )
            user.set_password(data.password)
            user.save()
            business = Business(
                name=data.company_name,
                created_by=user,
            )
            business.save()
            business_user = BusinessUser(
                business=business,
                user=user,
                role=data.role
            )
            business_user.save()
            return user
    raise HttpError(400, "Incorrect otp")


@router.patch("complete-company-profile", response=schemas.BusinessSchema, auth=JWTAuth())
def complete_company_profile(request, data: schemas.BusinessSchema):
    business_user = BusinessUser.objects.filter(user=request.user).first()
    if business_user:
        business = business_user.business
        if business.created_by == request.user:
            for key, value in data:
                setattr(business, key, value)
            business.logo = convert_base64_to_image_file(data.logo)
            business.save()
            return business
    else:
        raise HttpError(403, "Not allowed")