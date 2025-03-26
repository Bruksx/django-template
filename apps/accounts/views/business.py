from datetime import date
from typing import List
from uuid import UUID

from config.permissions import IsBusinessOwnerOrAdmin, IsBusinessUser
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from helpers.email.accounts import send_business_user_invitation_email, send_business_user_welcome_email
from helpers.email.auth import send_verification_code
from helpers.utils import convert_base64_to_image_file
from monkeypatches.q_cluster import async_task
from ninja import Router, UploadedFile, PatchDict, Form
from ninja.errors import HttpError
from monkeypatches.response import Response
from ninja_jwt.authentication import JWTAuth

from accounts.models import User, Business, BusinessUser, VerificationCode, Country, BusinessIndustry
from core.schemas import GenericNameAndUidSchema
from jobs.models import Job
from notification import notifications
from ..enums import UserType, BusinessUserStatusType, BusinessUserRoleType
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
                role=BusinessUserRoleType.OWNER.value,
            )
            business_user.save()
            return user
    raise HttpError(400, "Incorrect otp")


@router.patch("complete-company-profile", response=business_schema.BusinessSchema, auth=JWTAuth())
def complete_company_profile(request, data: business_schema.CompleteBusinessProfileSchema,):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    business: Business = business_user.business
    if business.created_by != request.user:
        raise HttpError(403, "Not allowed!")
    industry = get_object_or_404(BusinessIndustry, uid=data.industry_uid)
    country = get_object_or_404(Country, uid=data.country_uid)
    for key, value in data:
        if hasattr(business, key):
            setattr(business, key, value)
    business.logo = convert_base64_to_image_file(data.logo)
    business.industry = industry
    business.country = country
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
def upload_business_logo(request, file: UploadedFile):
    IsBusinessOwnerOrAdmin.check(request)
    """if not password:
        raise HttpError(400, "Password is required")
    if not request.user.check_password(password):
        raise HttpError(400, "Incorrect password")"""
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
    business: Business = request.user.businessuser.business
    if data.get("industry_uid"):
        industry_uid = data.pop("industry_uid")
        industry = get_object_or_404(BusinessIndustry, uid=industry_uid)
        business.industry = industry
    business.save()
    business.update(**data)
    return Response(status=200, data={"message": "Details updated successfully"})


@router.get("", auth=JWTAuth(), response=business_schema.BusinessDetailSchema)
def get_business_details(request):
    IsBusinessUser.check(request)
    return request.user.businessuser.business

@router.get("users", auth=JWTAuth(), response=List[business_schema.BusinessUserListSchema])
def get_business_users(request, search: str = ""):
    IsBusinessOwnerOrAdmin.check(request)
    business = request.user.businessuser.business
    query = Q()
    if search:
        query = (Q(user__first_name__icontains=search)
                 | Q(user__last_name__icontains=search)|
                 Q(user__email__icontains=search))

    return business.businessuser_set.filter(query).order_by("user__first_name", "user__last_name")

@router.post("users", auth=JWTAuth())
@transaction.atomic
def invite_business_user(request, data: business_schema.AddBusinessUserSchema):
    IsBusinessOwnerOrAdmin.check(request)
    business_user = request.user.businessuser
    business = business_user.business
    if BusinessUser.deleted_objects.filter(user__email__iexact=data.email).exists():
        raise HttpError(400, "This user's account has been deleted")
    if BusinessUser.objects.filter(user__email__iexact=data.email).exists():
        raise HttpError(400, "User with this email already exists")
    user = User.objects.create_user(
        first_name=data.first_name,
        last_name=data.last_name,
        type=UserType.BUSINESS.value,
        email=data.email,
        is_active=False
    )
    business_user = BusinessUser(
        business=business,
        user=user,
        role=data.role.value,
        status=BusinessUserStatusType.PENDING.value,
        added_by=business_user
    )
    business_user.save()
    async_task(send_business_user_invitation_email,
        user=user.fullname,
        email=user.email,
        business=business.name,
        user_uid=str(user.uid)
    )
    return Response(status=201, data={"message": "User invited successfully"})

@router.post("users/{business_user_uid}/resend-invite", auth=JWTAuth())
@transaction.atomic
def resend_business_user_invite(request, business_user_uid: UUID):
    IsBusinessOwnerOrAdmin.check(request)
    business = request.user.businessuser.business
    business_user = BusinessUser.objects.filter(uid=business_user_uid, business=business).first()
    if not business_user:
        raise HttpError(404, "User not found")
    if business_user.status == BusinessUserStatusType.ACTIVE.value:
        raise HttpError(400, "User is already active")
    async_task(send_business_user_invitation_email,
        user=business_user.user.fullname,
        email=business_user.user.email,
        business=business_user.business.name,
        user_uid=str(business_user.user.uid)
    )
    return Response(status=200, data={"message": "Invite resent successfully"})

@router.post("users/accept-invite")
@transaction.atomic
def accept_business_user_invite(request, data: business_schema.AcceptBusinessUserInviteSchema):
    business_user = BusinessUser.objects.filter(uid=data.code).first()
    if not business_user:
        raise HttpError(400, "This link is invalid")
    if business_user.user.is_active or business_user.user.email_verified:
        raise HttpError(400, "This link has expired")
    if business_user.status != BusinessUserStatusType.PENDING.value:
        raise HttpError(400, "You have already accepted this invite")
    user = business_user.user
    user.email_verified = True
    user.is_active = True
    user.save(update_fields=["email_verified", "is_active"])
    user.set_password(data.password)
    user.save()
    business_user.status = BusinessUserStatusType.ACTIVE.value
    business_user.save(update_fields=["status"])
    notifications.send_business_user_notification(
        business_user=business_user,
        action=notifications.EntityActionType.NEW,
        action_str="has joined your business"
    )
    async_task(send_business_user_welcome_email,
               user=user.fullname, email=user.email, business=business_user.business.name)
    return Response(status=200, data={"message": "You have successfully accepted the invite"})


@router.delete("users", auth=JWTAuth())
@transaction.atomic
def delete_account(request):
    IsBusinessUser.check(request)
    notifications.send_business_user_notification(
        business_user=request.user.businessuser,
        action=notifications.EntityActionType.DELETE,
        action_str="has deleted their account"
    )
    request.user.delete_account()
    return Response(status=204, data={"message": "Account deleted successfully"})


@router.get("industries", response=list[GenericNameAndUidSchema], tags=["Common"])
def get_business_industries(request):
    return BusinessIndustry.objects.all()