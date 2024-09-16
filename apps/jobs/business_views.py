from ninja import Router
from ninja.errors import HttpError
from .schemas import (
    EmploymentTypeSchema, CreateJobSchema, DepartmentSchema, RoleSchema, SkillCategorySchema, GenericNameAndUidSchema,
    JobDetailSchema
)
from .models import (
    EmploymentType, AvailableDay, Language, BusinessModel, JobLevel, JobPost, Job, ScreeningQuestion, QuestionOption,
)
from accounts.models import Department, Role, SkillCategory, Country, User, BusinessUser, Skill
from copy import copy
from django.db import transaction
from ninja_jwt.authentication import JWTAuth


router = Router(tags=["Business Jobs"])

@router.get("employment-types", response=list[EmploymentTypeSchema])
def get_employment_types(request):
    employment_types = EmploymentType.objects.filter(parent=None)
    return employment_types


@router.get("departments", response=list[DepartmentSchema])
def get_departments(request):
    return Department.objects.all()


@router.get("roles", response=list[RoleSchema])
def get_roles(request):
    return Role.objects.all()


@router.get("skill-categories", response=list[SkillCategorySchema])
def get_skills(request):
    return SkillCategory.objects.all().prefetch_related("skill_set")


@router.get("business-models", response=list[GenericNameAndUidSchema])
def get_business_models(request):
    return BusinessModel.objects.all()


@router.post("create", response=JobDetailSchema, auth=JWTAuth())
@transaction.atomic
def create_job(request, data:CreateJobSchema):
    business_user = BusinessUser.objects.filter(user=request.user).first()
    if not business_user:
        raise HttpError(403, "Not Allowed")
    job = Job.objects.create_job(business_user=business_user, data=data)
  
    return job