from typing import Optional
from uuid import UUID

from accounts.enums import UserType
from accounts.models import BusinessUser, Talent, Business
from accounts.schemas.admin import AdminDashboardFilter, BusinessMetricSchema, TalentMetricSchema, \
    BusinessListSchema, PaginatedBusinessJobListSchema, BusinessUserListSchema, MutateBusinessSchema, \
    MutateBusinessUserSchema, CreateBusinessSchema, TalentListSchema, TalentDetailSchema, \
    PaginatedApplicationListSchema, MutateTalentDetailSchema, BusinessActionSchema, PaginatedMetricFilter, \
    AccountStatusSchema, PauseResumeSchema, BusinessDetailSchema, BusinessFilter, BusinessUsersFilter, \
    TalentUsersFilter, BannedUserSchema
from accounts.schemas.common import UserSchema
from accounts.services import admin as admin_services
from django.db import transaction
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.responses import Response
from ninja_extra import paginate
from ninja_jwt.authentication import JWTAuth
from paginations import CustomPageNumberPaginationExtra, CustomPaginatedResponseSchema

from config.permissions import IsAdminUser

router = Router(tags=["Admin Account"])
pagination_class = lambda page_size: CustomPageNumberPaginationExtra(page_size=page_size or 50)


@router.get("business-metrics", auth=JWTAuth(), response=BusinessMetricSchema)
def get_admin_business_metrics(request, filters: AdminDashboardFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_admin_business_metrics_data(**filters.dict())

@router.get("talent-metric", auth=JWTAuth(), response=TalentMetricSchema)
def get_talent_metrics(request, filters: AdminDashboardFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_talent_metrics_data(**filters.dict(exclude_unset=True))

@router.get("businesses", auth=JWTAuth(), response=CustomPaginatedResponseSchema[BusinessListSchema])
@paginate(CustomPageNumberPaginationExtra, page_size=50)
def get_businesses(request, filters: BusinessFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_businesses_data(**filters.dict(exclude_unset=True))


@router.get("businesses/{business_uid}", auth=JWTAuth(), response=BusinessDetailSchema)
def get_business(request, business_uid:UUID):
    IsAdminUser.check(request)
    return admin_services.get_business_data(business_uid=business_uid)

@router.post("businesses", auth=JWTAuth(), response=BusinessListSchema)
@transaction.atomic
def add_business(request, data: CreateBusinessSchema):
    IsAdminUser.check(request)
    return admin_services.add_business_data(**data.dict(exclude_unset=True))

@router.patch("businesses/{business_uid}", auth=JWTAuth(), response=BusinessListSchema)
@transaction.atomic
def update_business(request, business_uid: UUID, data: MutateBusinessSchema):
    IsAdminUser.check(request)
    return admin_services.update_business_data(business_uid, **data.dict(exclude_unset=True))

# @router.post("businesses/{business_uid}", auth=JWTAuth(), response=BusinessListSchema)
# @transaction.atomic
# def business_action(request, business_uid: UUID, data: BusinessActionSchema):
#     IsAdminUser.check(request)
#     return admin_services.business_action(business_uid, data.action)

@router.get("businesses/{business_uid}/jobs", auth=JWTAuth(), response=PaginatedBusinessJobListSchema)
def get_business_jobs(request, business_uid: UUID, page_size=50, page=1):
    IsAdminUser.check(request)
    queryset, data = admin_services.get_business_jobs_data(business_uid)
    pagination = pagination_class(page_size).Input(page=page, page_size=page_size)
    return pagination_class(page_size).paginate_queryset(
        pagination=pagination,
        request=request,
        queryset=queryset, **data)

@router.get("businesses/{business_uid}/users", auth=JWTAuth(), response=CustomPaginatedResponseSchema[BusinessUserListSchema])
@paginate(CustomPageNumberPaginationExtra, page_size=50)
def get_business_users(request, business_uid: UUID, filters: BusinessUsersFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_business_users_data(business_uid, **filters.dict(exclude_unset=True))

@router.post("businesses/{business_uid}/users", auth=JWTAuth(), response=BusinessUserListSchema)
@transaction.atomic
def add_business_user(request, business_uid: UUID, data: MutateBusinessUserSchema):
    IsAdminUser.check(request)
    return admin_services.add_business_user_data(business_uid, **data.dict(exclude_unset=True))

@router.patch("businesses/users/{business_user_uid}", auth=JWTAuth(), response=BusinessUserListSchema)
@transaction.atomic
def update_business_user(request, business_user_uid: UUID, data: MutateBusinessUserSchema):
    IsAdminUser.check(request)
    return admin_services.update_business_user_data(business_user_uid, **data.dict(exclude_unset=True))


@router.delete("businesses/users/{business_user_uid}", auth=JWTAuth())
@transaction.atomic
def delete_business_user(request, business_user_uid: UUID):
    IsAdminUser.check(request)
    admin_services.delete_business_user_data(business_user_uid)
    return Response(status=204,data={"message": "Business user deleted successfully"})

@router.post("talents/{talent_uid}/ban", auth=JWTAuth())
@transaction.atomic
def ban_talent(request, talent_uid: UUID):
    IsAdminUser.check(request)
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "This talent does not exist")
    admin_services.ban_account(talent.user)
    return Response(status=200 ,data={"message": "Talent account has been banned successfully"})

@router.post("businesses/users/{business_user_uid}/login", auth=JWTAuth(), response=UserSchema)
@transaction.atomic
def log_in_as_business_user(request, business_user_uid: UUID):
    IsAdminUser.check(request)
    business_user = BusinessUser.objects.filter(uid=business_user_uid).first()
    if not business_user:
        raise HttpError(404, "This business user does not exist")
    return business_user.user

@router.post("talents/{talent_uid}/login", auth=JWTAuth(), response=UserSchema)
@transaction.atomic
def log_in_as_talent(request, talent_uid: UUID):
    IsAdminUser.check(request)
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "This talent does not exist")
    return talent.user

@router.post("businesses/users/{business_user_uid}/account-status", auth=JWTAuth(), response=BusinessUserListSchema)
@transaction.atomic
def toggle_business_user_account_status(request, business_user_uid: UUID, data: AccountStatusSchema):
    IsAdminUser.check(request)
    business_user = BusinessUser.objects.filter(uid=business_user_uid).first()
    if not business_user:
        raise HttpError(404, "This business user does not exist")
    user = admin_services.toggle_account_status(business_user.user, is_active=data.is_active)
    return user.businessuser

@router.post("talents/{talent_uid}/account-status", auth=JWTAuth(), response=TalentListSchema)
@transaction.atomic
def toggle_talent_account_status(request, talent_uid: UUID, data: AccountStatusSchema):
    IsAdminUser.check(request)
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "This talent does not exist")
    user = admin_services.toggle_account_status(talent.user, is_active=data.is_active)
    return user.talent


@router.get("talents", auth=JWTAuth(), response=CustomPaginatedResponseSchema[TalentListSchema])
@paginate(CustomPageNumberPaginationExtra, page_size=50)
def get_talent_users(request, filters: TalentUsersFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_talent_users_data(**filters.dict(exclude_unset=True))

@router.get("talents/{talent_uid}", auth=JWTAuth(), response=TalentDetailSchema)
def get_talent_user(request, talent_uid: UUID):
    IsAdminUser.check(request)
    return admin_services.get_talent_user_data(talent_uid)

@router.get("talents/{talent_uid}/applications", auth=JWTAuth(), response=PaginatedApplicationListSchema)
def get_talent_applications(request, talent_uid: UUID, page_size=50, page=1):
    IsAdminUser.check(request)
    queryset, data = admin_services.get_talent_applications_data(talent_uid)
    pagination = pagination_class(page_size).Input(page=page, page_size=page_size)
    return pagination_class(page_size).paginate_queryset(
        pagination=pagination,
        request=request,
        queryset=queryset,
        **data)

@router.post("talents", auth=JWTAuth(), response=TalentDetailSchema)
@transaction.atomic
def create_talent_user(request, data: MutateTalentDetailSchema):
    IsAdminUser.check(request)
    return admin_services.create_talent_user_data(**data.dict(exclude_unset=True))

@router.patch("talents/{talent_uid}", auth=JWTAuth(), response=TalentDetailSchema)
@transaction.atomic
def update_talent_user(request, talent_uid: UUID, data: MutateTalentDetailSchema):
    IsAdminUser.check(request)
    return admin_services.update_talent_user_data(talent_uid, **data.dict(exclude_unset=True))

@router.get("metrics/pages", auth=JWTAuth())
def get_page_metrics(request, filters: PaginatedMetricFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_page_metric_data(**filters.dict(exclude_unset=True))


@router.get("metrics/api", auth=JWTAuth())
def get_api_metrics(request, filters: PaginatedMetricFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_api_metric_data(**filters.dict(exclude_unset=True))


@router.get("metrics/talent/signups", auth=JWTAuth())
def get_talent_signups(request, filters: PaginatedMetricFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_talent_signups_data(**filters.dict(exclude_unset=True))

@router.get("metrics/talent/profile-completion", auth=JWTAuth())
def get_talent_profile_completion(request, filters: PaginatedMetricFilter = Query(...)):
    IsAdminUser.check(request)
    return admin_services.get_talent_profile_completion_data(**filters.dict(exclude_unset=True))


@router.post("businesses/{business_uid}/resumption", auth=JWTAuth(), response=BusinessListSchema)
def pause_resume_business(request, business_uid: UUID, data: PauseResumeSchema):
    IsAdminUser.check(request)
    business = Business.objects.filter(uid=business_uid).first()
    if not business:
        raise HttpError(404, "This business does not exist")
    return admin_services.pause_resume_business(business, data.action)


@router.delete("businesses/{business_uid}", auth=JWTAuth())
def delete_business(request, business_uid: UUID):
    IsAdminUser.check(request)
    business = Business.objects.filter(uid=business_uid).first()
    if not business:
        raise HttpError(404, "This business does not exist")
    admin_services.delete_business(business)
    return Response(status=204, data={"message": "Business deleted successfully"})

@router.get("banned-accounts", auth=JWTAuth(), response=CustomPaginatedResponseSchema[BannedUserSchema])
@paginate(CustomPageNumberPaginationExtra, page_size=50)
def get_banned_accounts(request, account_type:Optional[UserType]=None):
    IsAdminUser.check(request)
    return admin_services.get_banned_users_data(account_type=account_type)


@router.post("banned-accounts/{account_uid}", auth=JWTAuth())
def unban_account(request, account_uid: UUID):
    IsAdminUser.check(request)
    return admin_services.unban_user_account(account_uid)
