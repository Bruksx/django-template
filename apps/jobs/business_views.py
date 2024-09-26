from ninja import Router
from ninja.errors import HttpError
from .schemas import (
    EmploymentTypeSchema, CreateJobSchema, DepartmentSchema, RoleSchema, SkillCategorySchema, GenericNameAndUidSchema,
    JobDetailSchema
)
from .models import (
    EmploymentType, AvailableDay, Language, BusinessModel, JobLevel, JobPost, Job, ScreeningQuestion, QuestionOption,
    RequiredAttribute
)
from accounts.models import Department, Role, SkillCategory, Country, User, BusinessUser, Skill
from copy import copy
from django.db import transaction
from ninja_jwt.authentication import JWTAuth
from . import schemas as job_schemas
from uuid import UUID
from django.shortcuts import get_object_or_404
from ninja_extra.pagination import (
    paginate, PageNumberPaginationExtra, PaginatedResponseSchema
)


router = Router(tags=["Business Jobs"])

@router.get("employment-types", response=list[EmploymentTypeSchema], tags=["Common"])
def get_employment_types(request):
    employment_types = EmploymentType.objects.filter(parent=None)
    return employment_types


@router.get("departments", response=list[DepartmentSchema], tags=["Common"])
def get_departments(request):
    return Department.objects.all()


@router.get("roles", response=list[RoleSchema], tags=["Common"])
def get_roles(request):
    return Role.objects.all()


@router.get("skill-categories", response=list[SkillCategorySchema], tags=["Common"])
def get_skills(request):
    return SkillCategory.objects.all().prefetch_related("skill_set")


@router.get("business-models", response=list[GenericNameAndUidSchema])
def get_business_models(request):
    return BusinessModel.objects.all()


@router.post("", response=JobDetailSchema, auth=JWTAuth())
@transaction.atomic
def create_job(request, data:CreateJobSchema):
    business_user = BusinessUser.objects.filter(user=request.user).first()
    if not business_user:
        raise HttpError(403, "Not Allowed")
    job = Job.objects.create_job(business_user=business_user, data=data)
    return job


@router.patch("set-required-attributes/{job_uid}", response=job_schemas.RequiredAttributeSchema, auth=JWTAuth())
def set_required_attributes(request, data:job_schemas.MutateRequiredAttributeSchema, job_uid:UUID):
    request_data = data.dict()
    job = Job.objects.filter(created_by=request.user, uid=job_uid).first()
    if not job:
        raise HttpError(404, "Job not found")
    if job.created_by != request.user:
        raise HttpError(403, "not allowed")
    required_attributes, _ = RequiredAttribute.objects.get_or_create(job=job)
    required_attributes.skills.set(request_data.pop("skills"))
    required_attributes.business_model.set(request_data.pop("business_model"))
    required_attributes.update(**request_data)
    return required_attributes


@router.patch("job-post/{job_post_uid}/post", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
def post_job_post(request, job_post_uid: UUID):
    business_user = BusinessUser.objects.filter(user=request.user).first()
    if not business_user:
        raise HttpError(403, "Not Allowed")
    job_post = get_object_or_404(JobPost, uid=job_post_uid, job__created_by=business_user)
    job_post.update(is_posted=True)
    return job_post


@router.delete("job-post/{job_post_uid}", auth=JWTAuth())
def delete_job_post(request, job_post_uid:UUID):
    business_user = BusinessUser.objects.filter(user=request.user).first()
    if not business_user:
        raise HttpError(403, "Not Allowed")
    get_object_or_404(JobPost, uid=job_post_uid, job__created_by=business_user).delete()
    return {"message": "deleted"}


@router.put("job-post/{job_post_uid}", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
def edit_job_post(request, job_post_uid, data: job_schemas.JobPostDetailSchema):
    business_user = BusinessUser.objects.filter(user=request.user).first()
    if not business_user:
        raise HttpError(403, "Not Allowed")
    job_post = get_object_or_404(JobPost, uid=job_post_uid, job__created_by=business_user)
    del data.uid
    job_post.update(**data.dict())
    return job_post


@router.post("job-post/add/{job_uid}", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
def add_job_post(request, job_uid:UUID, data: job_schemas.MutateJobPostSchema):
    business_user = BusinessUser.objects.filter(user=request.user).first()
    if not business_user:
        raise HttpError(403, "Not Allowed")
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


"TODO: add custom pagination class to control page size"
@router.get("list", response=PaginatedResponseSchema[JobDetailSchema], auth=JWTAuth())
@paginate(PageNumberPaginationExtra, page_size=50)
def job_list(request):
    business_user = BusinessUser.objects.filter(user=request.user).first()
    if not business_user:
        raise HttpError(403, "Not Allowed")
    return Job.objects.filter(created_by=business_user)