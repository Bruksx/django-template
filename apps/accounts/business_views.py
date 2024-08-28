from ninja import Router
from . import schemas
from .models import User, Business, BusinessUser, VerificationCode
from django.core.mail import send_mail



router = Router()


@router.post("create-account/")
def register_business(request, data: schemas.RegisterSchema):
    verification_code = VerificationCode(email=data.email)
    raw_code = verification_code.save()
    del data.password
    send_mail(
        "OTP",
        f"{raw_code}",
        "from@example.com",
        [data.email],
        fail_silently=False,
    )
    return data