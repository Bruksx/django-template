from datetime import date
from typing import List
from uuid import UUID

from config.permissions import IsBusinessOwnerOrAdmin, IsBusinessUser
from django.db import transaction
from helpers.email.users import send_verification_code
from helpers.utils import convert_base64_to_image_file
from monkeypatches.q_cluster import async_task
from ninja import Router, UploadedFile, PatchDict, Form
from ninja.errors import HttpError
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth

from accounts.models import User, Business, BusinessUser, VerificationCode
from jobs.models import Job
from ..enums import UserType
from ..schemas import business as business_schema
from ..schemas import common as common_schema

router = Router(tags=["Business Account"])


@router.post("initiate-account-creation")
def initiate_account_creation(request, data: common_schema.RegisterSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode(email=data.email)
    raw_code = verification_code.save()
    async_task(send_verification_code, email=data.email, code=raw_code, user="", company=None)
    return {
        "message": "verification mail sent!"
    }


@router.post("create-account", response={200:common_schema.UserSchema})
@transaction.atomic
def create_account(request, data: business_schema.ValidateOTPSchema):
    existing_user = User.objects.filter(email=data.email).exists()
    if existing_user:
        raise HttpError(400, "An account with this email already exists")
    verification_code = VerificationCode.objects.filter(email=data.email).last()
    if verification_code:
        is_correct = verification_code.verify_code(data.otp)
        if is_correct:
            user = User.objects.create(
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


@router.patch("complete-company-profile", response=business_schema.BusinessSchema, auth=JWTAuth())
def complete_company_profile(request, data: business_schema.BusinessSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    business = business_user.business
    if business.created_by == request.user:
        for key, value in data:
            setattr(business, key, value)
        business.logo = convert_base64_to_image_file(data.logo)
        business.save()
    return business

@router.get("dashboard", auth=JWTAuth(), response={200: business_schema.DashboardSchema})
def business_dashboard(request, start_date: date=None, end_date: date=None, role_id: UUID=None, client: str=None):
    # will require caching
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    business = business_user.business
    context = dict(
        start_date=start_date,
        end_date=end_date,
        role_id=role_id,
        client=client
    )
    return Response(data=business_schema.DashboardSchema.from_orm(business, context=context))


@router.get("job-clients", auth=JWTAuth(), response={200: List[str]})
def get_job_clients(request):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    return Response(data=list(Job.objects.filter(created_by__business=business_user.business,
                                                hiring_company_name__isnull=False).only("hiring_company_name")\
                  .distinct("hiring_company_name").values_list("hiring_company_name", flat=True)))


@router.post("logo", auth=JWTAuth())
@transaction.atomic()
def upload_business_logo(request, file: UploadedFile,
                         password:str = Form()):
    IsBusinessOwnerOrAdmin.check(request)
    if not password:
        raise HttpError(400, "Password is required")
    if not request.user.check_password(password):
        raise HttpError(400, "Incorrect password")
    extension = file.name.split(".")[-1]
    if extension not in ["jpg", "jpeg", "png"]:
        raise HttpError(400, "This file type is not supported. Only JPG/JPEG/PNG files")
    business = request.user.businessuser.business
    async_task(business.update, logo=file)
    return Response(status=200, data={"message": "Logo uploaded successfully"})

@router.patch("", auth=JWTAuth())
@transaction.atomic()
def update_business_details(request, data: PatchDict[business_schema.MutateBusinessSchema]):
    IsBusinessOwnerOrAdmin.check(request)
    password = data.pop("password", None)
    if not password:
        raise HttpError(400, "Password is required")
    if not request.user.check_password(password):
        raise HttpError(400, "Incorrect password")
    business = request.user.businessuser.business
    business.update(**data)
    return Response(status=200, data={"message": "Details updated successfully"})


@router.get("", auth=JWTAuth(), response=business_schema.BusinessDetailSchema)
def get_business_details(request):
    IsBusinessUser.check(request)
    return request.user.businessuser.business


