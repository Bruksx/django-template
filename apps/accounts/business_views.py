from ninja import Router
from . import schemas
from .models import User, Business, BusinessUser, VerificationCode
from django.core.mail import send_mail
from django.db import transaction
from ninja.errors import HttpError


router = Router()


@router.post("create-account/")
def create_account(request, data: schemas.RegisterSchema):
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
    verification_code = VerificationCode.objects.filter(email=data.email).last()
    if verification_code:
        is_correct = verification_code.verify_code(data.otp)
        if is_correct:
            user = User.objects.create(
                role=data.role,
                password=data.password,
                first_name=data.first_name,
                last_name=data.last_name,
                type= User.TALENT,
                email=data.email,
                username=None,
            )
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