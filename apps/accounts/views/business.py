from datetime import date
from enum import Enum
from typing import List
from uuid import UUID

from config.permissions import IsBusinessOwnerOrAdmin, IsBusinessUser
from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from django.shortcuts import get_object_or_404
from helpers.email.accounts import send_business_user_invitation_email, send_business_user_welcome_email
from helpers.email.auth import send_verification_code
from helpers.email.utils import send_email
from helpers.utils import convert_base64_to_image_file
from monkeypatches.q_cluster import async_task
from monkeypatches.response import Response
from ninja import Router, UploadedFile, PatchDict, Form
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from accounts.models import User, Business, BusinessUser, VerificationCode, Country, BusinessIndustry, TalentFilter, \
    Skill, Role
from core.models import Language
from core.schemas import GenericNameAndUidSchema
from jobs.models import Job, JobPost
from jobs.schemas import BusinessUserJobSchema
from notification import notifications
from ..enums import UserType, BusinessUserStatusType, BusinessUserRoleType
from ..schemas import business as business_schema
from ..schemas import common as common_schema
from ..schemas.business import SendEmailSchema, MutateTalentFilterSchema, TalentFilterSchema, TalentFilterListSchema
from ..services import create_business_workflows

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
    if not verification_code:
        raise HttpError(400, "Invalid otp")
    is_correct = verification_code.verify_code(data.otp)
    if not is_correct:
        raise HttpError(400, "Invalid otp")
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
    async_task(create_business_workflows, business.id)
    return user


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
    if role_id:
        role = Role.objects.filter(uid=role_id).first()
        if not role:
            raise HttpError(404, "Role not found")
        role_id = role.id
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
def upload_business_logo(request, file: UploadedFile=None):
    IsBusinessOwnerOrAdmin.check(request)
    """if not password:
        raise HttpError(400, "Password is required")
    if not request.user.check_password(password):
        raise HttpError(400, "Incorrect password")"""
    business: Business = request.user.businessuser.business
    if file:
        extension = file.name.split(".")[-1]
        if extension not in ["jpg", "jpeg", "png"]:
            raise HttpError(400, "This file type is not supported. Only JPG/JPEG/PNG files")
        business.logo = file
        #async_task(business.save)
        business.update(logo=file)
    else:
        business.logo = None
        business.save()
    return Response(status=200, data={"message": "Logo updated successfully"})


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
def get_business_users(request, search: str = "", role: BusinessUserRoleType = None):
    IsBusinessOwnerOrAdmin.check(request)
    business = request.user.businessuser.business
    query = Q()
    if search:
        query = (Q(user__first_name__icontains=search)
                 | Q(user__last_name__icontains=search)|
                 Q(user__email__icontains=search))
    if role:
        query = query & Q(role=role.value)

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

@router.post("users/transfer-role", auth=JWTAuth())
@transaction.atomic
def transfer_business_user_role(request, data: business_schema.TransferRoleSchema):
    IsBusinessOwnerOrAdmin.check(request)
    business = request.user.businessuser.business
    previous_assignee = business.businessuser_set.filter(uid=data.from_business_user).first()
    if not previous_assignee:
        raise HttpError(404, "Previous Assignee not found")
    new_assignee = business.businessuser_set.filter(uid=data.to_business_user).first()
    if not new_assignee:
        raise HttpError(404, "New Assignee not found")
    if previous_assignee.role:
        new_assignee.role = previous_assignee.role
        new_assignee.save()
    return Response(status=200, data={"message": "Role transferred successfully"})


@router.get("users/{business_user_uid}/", auth=JWTAuth(), response=business_schema.BusinessUserListSchema)
def get_business_user(request, business_user_uid):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    business = business_user.business
    staff_user = get_object_or_404(BusinessUser, uid=business_user_uid, business=business)
    return staff_user


@router.patch("users/{business_user_uid}/", auth=JWTAuth())
@transaction.atomic
def update_business_user(request, business_user_uid, data: PatchDict[business_schema.MutateBusinessUserSchema]):
    IsBusinessOwnerOrAdmin.check(request)
    business_user = request.user.businessuser
    business = business_user.business
    data_dict = data
    email = data_dict.get("email")
    staff_user = get_object_or_404(BusinessUser, uid=business_user_uid, business=business)
    if email:
        if email != staff_user.user.email:
            if User.global_objects.filter(email=data["email"]).exists():
                raise HttpError(400, "This email is not available")
    role = data_dict.get("role")
    if role:
        role = role.value
        if role == BusinessUserRoleType.OWNER.value and business_user.role != BusinessUserRoleType.OWNER.value:
            raise HttpError(400, "You cannot assign owner role to this user")
        if business_user.role == BusinessUserRoleType.OWNER.value and staff_user == business_user and role != BusinessUserRoleType.OWNER.value:
            raise HttpError(400, "You cannot change your role until you have transferred it")
        if business_user.role != BusinessUserRoleType.OWNER.value and role != BusinessUserRoleType.OWNER.value and staff_user.role == BusinessUserRoleType.OWNER.value:
            raise HttpError(400, "You cannot update the role of the owner")



    user = staff_user.user
    for key, value in data_dict.items():
        if hasattr(user, key):
            if isinstance(value, str):
                value = value.strip()
            if isinstance(value, Enum):
                value = value.value
            setattr(user, key, value)
    user.save()

    for key, value in data_dict.items():
        if hasattr(staff_user, key):
            if isinstance(value, str):
                value = value.strip()
            if isinstance(value, Enum):
                value = value.value
            setattr(staff_user, key, value)
    staff_user.save()
    if staff_user.role == BusinessUserRoleType.OWNER.value and business_user.role == BusinessUserRoleType.OWNER.value:
        business_user.update(role=BusinessUserRoleType.ADMIN.value)
    return Response(status=201, data={"message": "User updated successfully"})


@router.post("users/{business_user_uid}/reassign-job-posts/", auth=JWTAuth())
def reassign_job_posts(request, business_user_uid, data:business_schema.ReassignJobPostInputSchema):
    IsBusinessOwnerOrAdmin.check(request)
    business_user: BusinessUser = request.user.businessuser
    business = business_user.business
    staff = get_object_or_404(BusinessUser, uid=business_user_uid, business=business)
    nominee = get_object_or_404(BusinessUser, uid=data.nominee_uid, business=business)
    JobPost.objects.filter(recruiter=staff).update(recruiter=nominee)
    return Response(status=200, data={"message": "Job posts reassigned successfully"})


@router.get("users/{business_user_uid}/jobs/", auth=JWTAuth(), response=list[BusinessUserJobSchema])
def business_user_jobs(request, business_user_uid):
    IsBusinessOwnerOrAdmin.check(request)
    business_user = request.user.businessuser
    business = business_user.business
    staff_user = get_object_or_404(BusinessUser, uid=business_user_uid)
    if staff_user.business != business:
        raise HttpError(403, "Not allowed! This user is not in your organization")
    jobs = Job.objects.annotate(
            is_posted_by_business_user=Exists(
                JobPost.objects.filter(
                    job__pk=OuterRef("pk"), posted_by=business_user
                )
            ),
            is_recruiter=Exists(
                JobPost.objects.filter(
                    job__pk=OuterRef("pk"), recruiter=business_user
                )
            )
        ).filter(
            Q(created_by=business_user) |
            Q(is_posted_by_business_user=True) |
            Q(is_recruiter=True)
    ).order_by("-updated_at")
    return jobs


@router.delete("users/{business_user_uid}/", auth=JWTAuth())
@transaction.atomic()
def delete_business_user(request, business_user_uid):
    IsBusinessOwnerOrAdmin.check(request)
    user: User = request.user
    business_user = request.user.businessuser
    business = business_user.business
    staff_user = get_object_or_404(BusinessUser, uid=business_user_uid, business=business)
    if staff_user.user == user:
        raise HttpError(403, "Not allowed! you cannot delete your account")
    if staff_user.role == BusinessUserRoleType.OWNER.value:
        raise HttpError(403, "Not allowed! you cannot delete owner account")
    has_jobs = Job.objects.annotate(
            is_posted_by_business_user=Exists(
                JobPost.objects.filter(
                    job__pk=OuterRef("pk"), posted_by=staff_user
                )
            ),
            is_recruiter=Exists(
                JobPost.objects.filter(
                    job__pk=OuterRef("pk"), recruiter=staff_user
                )
            )
        ).filter(
            is_recruiter=True
    ).exists()
    if has_jobs and staff_user.status != BusinessUserStatusType.PENDING.value:
        raise HttpError(403, "Not Allowed! Please reassign all jobs allocated to this user before proceeding with deletion")
    staff_user.user.delete_account()
    return Response(status=201, data={"message": "User updated successfully"})


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


@router.post("email-talents", auth=JWTAuth())
def send_email_to_talents(request, data:SendEmailSchema=Form(), attachments: List[UploadedFile]=None):
    IsBusinessUser.check(request)
    async_task(send_email, subject=data.subject, emails=data.emails, plain_body=data.body, attachments=attachments,
               from_user=data.from_email)
    return Response(status=200, data={"message": "Email sent successfully"})


@router.post("talents-filters", auth=JWTAuth(), tags=["Talent Jobs"], response=TalentFilterSchema)
@transaction.atomic
def create_talent_filter(request, data: PatchDict[MutateTalentFilterSchema]):
    IsBusinessUser.check(request)
    name = data.get("name")
    if not name:
        raise HttpError(400, "Name is required")
    if TalentFilter.objects.filter(business_user=request.user.businessuser, name__iexact=name).exists():
        raise HttpError(400, "Name already exists")
    business_user = request.user.businessuser
    if data.get("work_structure"):
        data["work_structure"] = data["work_structure"].value
    languages = data.pop("languages", None)
    skills = data.pop("skills", None)
    if languages is not None:
        languages = Language.objects.filter(uid__in=languages)
    if skills is not None:
        skills = Skill.objects.filter(uid__in=skills)

    talent_filter = TalentFilter.objects.create(business_user=business_user, **data)
    if languages:
        talent_filter.languages.set(languages)
    else:
        talent_filter.languages.clear()
    if skills:
        talent_filter.skills.set(skills)
    else:
        talent_filter.skills.clear()
    talent_filter.save()
    return talent_filter

@router.patch("talents-filters/{talent_filter_uid}", auth=JWTAuth(), tags=["Talent Jobs"], response=TalentFilterSchema)
@transaction.atomic
def update_talent_filter(request, talent_filter_uid: UUID, data: PatchDict[MutateTalentFilterSchema]):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    talent_filter = TalentFilter.objects.filter(uid=talent_filter_uid, business_user=business_user).first()
    if not talent_filter:
        raise HttpError(404, "Talent filter not found")
    name = data.get("name")
    if (name and TalentFilter.objects.filter(business_user=request.user.businessuser, name__iexact=name)
            .exclude(id=talent_filter.id).exists()):
        raise HttpError(400, "Name already exists")

    if data.get("work_structure"):
        data["work_structure"] = data["work_structure"].value
    languages = data.pop("languages", None)
    skills = data.pop("skills", None)
    if languages is not None:
        languages = Language.objects.filter(uid__in=languages)
    if skills is not None:
        skills = Skill.objects.filter(uid__in=skills)

    talent_filter = talent_filter.update(**data)
    if languages:
        talent_filter.languages.set(languages)
    else:
        talent_filter.languages.clear()
    if skills:
        talent_filter.skills.set(skills)
    else:
        talent_filter.skills.clear()
    talent_filter.save()
    return talent_filter



@router.get("talents-filters", auth=JWTAuth(), tags=["Talent Jobs"], response=List[TalentFilterListSchema])
def get_talent_filters(request):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    return TalentFilter.objects.filter(business_user=business_user).order_by("name")


@router.get("talents-filters/{talent_filter_uid}", auth=JWTAuth(), tags=["Talent Jobs"], response=TalentFilterSchema)
def get_talent_filter(request, talent_filter_uid: UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    talent_filter = TalentFilter.objects.filter(business_user=business_user, uid=talent_filter_uid).first()
    if not talent_filter:
        raise HttpError(404, "Talent filter not found")
    return talent_filter





