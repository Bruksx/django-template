from uuid import UUID

from config.permissions import IsBusinessUser
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Response
from ninja_extra.pagination import (
    paginate, PageNumberPaginationExtra, PaginatedResponseSchema
)
from ninja_jwt.authentication import JWTAuth

from accounts.models import Department, Role, SkillCategory, Country
from . import schemas as job_schemas
from .enums import JobStatusType
from .models import (
    EmploymentType, BusinessModel, JobLevel, JobPost, Job, RequiredAttribute
)
from .schemas import (
    EmploymentTypeSchema, CreateJobSchema, DepartmentSchema, RoleSchema, SkillCategorySchema, GenericNameAndUidSchema,
    JobFullDetailSchema, JobLevelSchema, TalentListJobPostSchema
)

router = Router(tags=["Business Jobs"])

@router.get("employment-types", response=list[EmploymentTypeSchema], tags=["Common"])
def get_employment_types(request, search=""):
    queryset = EmploymentType.objects.filter(parent=None)
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset


@router.get("departments", response=list[DepartmentSchema], tags=["Common"])
def get_departments(request, search=""):
    queryset = Department.objects.prefetch_related("industry").all()
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(industry__name__icontains=search))
    return queryset


@router.get("roles", response=list[RoleSchema], tags=["Common"])
def get_roles(request, search=""):
    queryset = Role.objects.prefetch_related("department").all()
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(department__name__icontains=search))
    return queryset

@router.get("job-levels", response=list[JobLevelSchema], tags=["Common"])
def get_job_levels(request, search=""):
    queryset = JobLevel.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset


@router.get("skill-categories", response={200: list[SkillCategorySchema]}, tags=["Common"])
def get_skills(request, search=""):
    queryset = SkillCategory.objects.all().prefetch_related("skill_set")
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(skill__name__icontains=search)).distinct("uid")
    return Response(data=[SkillCategorySchema.from_orm(q, context={"search": search}) for q in queryset])


@router.get("business-models", response=list[GenericNameAndUidSchema], tags=["Common"])
def get_business_models(request, search=""):
    queryset = BusinessModel.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset


@router.post("", response=JobFullDetailSchema, auth=JWTAuth())
@transaction.atomic
def create_job(request, data:CreateJobSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job = Job.objects.create_job(business_user=business_user, data=data)
    return job


@router.patch("set-required-attributes/{job_uid}", response=job_schemas.RequiredAttributeSchema, auth=JWTAuth())
def set_required_attributes(request, data:job_schemas.MutateRequiredAttributeSchema, job_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    request_data = data.dict()
    user = request.user
    job = Job.objects.filter(created_by=business_user, uid=job_uid).first()
    if not job:
        raise HttpError(404, "Job not found")
    if job.created_by != user.businessuser:
        raise HttpError(403, "not allowed")
    required_attributes, _ = RequiredAttribute.objects.get_or_create(job=job)
    required_attributes.skills.set(request_data.pop("skills"))
    required_attributes.business_model.set(request_data.pop("business_model"))
    required_attributes.update(**request_data)
    return required_attributes


@router.patch("job-post/{job_post_uid}/post", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
def post_job_post(request, job_post_uid: UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_post = get_object_or_404(JobPost, uid=job_post_uid, job__created_by=business_user)
    job_post.update(status=JobStatusType.POSTED.value)
    return job_post


@router.delete("job-post/{job_post_uid}", auth=JWTAuth())
def delete_job_post(request, job_post_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    get_object_or_404(JobPost, uid=job_post_uid, job__created_by=business_user).delete()
    return {"message": "deleted"}


@router.put("job-post/{job_post_uid}", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
def edit_job_post(request, job_post_uid, data: job_schemas.JobPostDetailSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_post = get_object_or_404(JobPost, uid=job_post_uid, job__created_by=business_user)
    del data.uid
    job_post.update(**data.dict())
    return job_post


@router.post("job-post/add/{job_uid}", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
def add_job_post(request, job_uid:UUID, data: job_schemas.MutateJobPostSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job = get_object_or_404(Job, uid=job_uid, created_by=business_user)
    request_data = data.dict()
    annual_bonus_currency = request_data.pop("annual_bonus_currency_uid")
    annual_salary_currency = request_data.pop("annual_salary_currency_uid")
    country = get_object_or_404(Country, code=request_data.pop("country_code"))
    job_post = JobPost(
        **request_data,
        job=job,
        country=country,
        annual_bonus_currency = annual_bonus_currency,
        annual_salary_currency = annual_salary_currency,
    )
    job_post.save()
    return job_post

@router.get("job-posts/{job_post_uid}/talents", response=list[TalentListJobPostSchema], auth=JWTAuth())
def get_talents_by_job_post(request, job_post_uid: UUID, search: str=None):
    IsBusinessUser.check(request)
    job_post = JobPost.objects.filter(uid=job_post_uid).first()
    if not job_post:
        raise HttpError(404, "Job Post not found")
    request.context = dict(job_post=job_post)
    query = Q()
    if search:
        query = Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search)
    return job_post.get_talents().filter(query)


"TODO: add custom pagination class to control page size"
@router.get("list", response=PaginatedResponseSchema[JobFullDetailSchema], auth=JWTAuth())
@paginate(PageNumberPaginationExtra, page_size=50)
def job_list(request):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    return Job.objects.filter(created_by=business_user)
