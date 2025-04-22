from typing import List

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from helpers.email.auth import send_verification_code
from monkeypatches.q_cluster import async_task
from monkeypatches.response import Response
from ninja import Router
from ninja.errors import HttpError
from ninja_extra import paginate
from ninja_jwt.authentication import JWTAuth

from accounts.models import Talent, Country, EducationLevel, CustomerCase, User, VerificationCode, TalentFilter, \
    Industry
from accounts.schemas import common as common_schemas
from accounts.schemas import talent as talent_schemas
from core.schemas import GenericNameAndUidSchema
from paginations import CustomPageNumberPaginationExtra, CustomPaginatedResponseSchema

router = Router(tags=["Common Account APIs"])


@router.get("talents", response=CustomPaginatedResponseSchema[talent_schemas.TalentUserListSchema], auth=JWTAuth())
@paginate(CustomPageNumberPaginationExtra, page_size=50)
def talent_lists(request, search="", apply_filter=False):
    talents = Talent.objects.prefetch_related("user").filter(visible=True)
    if search:
        talents = talents.filter(Q(user__first_name__icontains=search)|
                                 Q(user__last_name__icontains=search)|
                                 Q(user__email__icontains=search)
                                 )
    if apply_filter is True and hasattr(request.user, "businessuser"):
        if not hasattr(request.user.businessuser, "talentfilter"):
            talent_filter = TalentFilter.objects.create(business_user=request.user.businessuser)
        else:
            talent_filter = request.user.businessuser.talentfilter
        talents = talent_filter.get_queryset(talents)

    return talents.order_by("-user__last_login")


@router.get("countries", response=List[talent_schemas.CountrySchema], tags=["Common"])
def country_list(request, search:str=""):
    queryset = Country.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset


@router.get("educational-levels", response=List[talent_schemas.EducationLevelSchema], 
            tags=["Common"])
def educational_levels(request, search=""):
    queryset = EducationLevel.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset

@router.post("customer-cases", auth=JWTAuth())
def create_customer_case(request, data:common_schemas.MutateCustomerCaseSchema):
    user = request.user
    data = data.dict()
    data["reason"] = data["reason"].value
    if user.customercase_set.filter(**data).exists():
        raise HttpError(400, "Case already exists")
    CustomerCase.objects.create(**data, user=user).save()
    return Response(status=200, data={"message": "Case created successfully"})

@router.get("customer-cases", auth=JWTAuth(), response=List[common_schemas.CustomerCaseSchema])
def customer_case_list(request):
    user = request.user
    return user.customercase_set.order_by("-id")

@router.post("initiate-email-change", auth=JWTAuth())
@transaction.atomic
def initiate_email_change(request, data: common_schemas.InitiateEmailChangeSchema):
    user = request.user
    if data.email == user.email:
        raise HttpError(400, "Your current email is the same as the new one")
    if User.objects.filter(email=data.email).exclude(id=user.id).exists():
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode(email=data.email)
    raw_code = verification_code.save()
    async_task(send_verification_code, email=data.email, code=raw_code, user=user.get_full_name(), company=None)
    return Response(data={"message": "please check your email address for otp code"})


@router.post("change-email", auth=JWTAuth())
@transaction.atomic
def change_email(request, data: common_schemas.ChangeEmailSchema):
    verification_code = VerificationCode.objects.filter(email=data.email).last()
    if not verification_code:
        raise HttpError(400, "Invalid otp")
    correct_otp = verification_code.verify_code(data.otp)
    if not correct_otp:
        raise HttpError(400, "Incorrect otp")
    user = request.user
    if User.objects.filter(email=data.email).exclude(id=user.id).exists():
        raise HttpError(400, "An account with this email already exists")
    user.email = data.email
    user.save(update_fields=["email"])
    verification_code.delete()
    return Response(data={"message": "email changed successfully"})

@router.post("change-password", auth=JWTAuth())
@transaction.atomic
def password_change(request, data: common_schemas.ChangePasswordSchema):
    user = request.user
    if not user.check_password(data.old_password):
        raise HttpError(400, "Incorrect password")
    user.set_password(data.new_password)
    user.save()
    return Response(data={"message": "password changed successfully"})

@router.post("change-phone-number", auth=JWTAuth())
@transaction.atomic
def phone_number_change(request, data: common_schemas.ChangePhoneSchema):
    user = request.user
    if not user.check_password(data.password):
        raise HttpError(400, "Incorrect password")
    user.phone_number = data.phone_number
    user.save()
    return Response(data={"message": "phone number changed successfully"})

@router.post("send-email-otp")
@transaction.atomic
def send_otp_to_email(request, data: common_schemas.SendEmailOtpSchema):
    VerificationCode.objects.filter(expires_at__lt=timezone.now(), email=data.email).delete()
    user = User.objects.filter(email__iexact=data.email).first()
    if not user:
        raise HttpError(404, "An account with this email does not exist")
    VerificationCode.objects.filter(email__iexact=data.email).hard_delete()
    verification = VerificationCode.objects.create(email=data.email)
    verification = verification.update(code=VerificationCode.default_code())
    async_task(send_verification_code, email=data.email, code=verification.code, user=user.fullname, company=None)
    return Response(data={"message": "please check your email address for otp code"})

@router.get("industries", response=list[GenericNameAndUidSchema], tags=["Common"])
def get_industries(request, search=""):
    if search:
        return Industry.objects.filter(name__icontains=search)
    return Industry.objects.all()
