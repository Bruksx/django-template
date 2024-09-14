from ninja import Router
from .schemas import EmploymentTypeSchema, CreateJobSchema, DepartmentSchema, RoleSchema, SkillCategorySchema
from .models import EmploymentType, AvailableDay, Language
from accounts.models import Department, Role, SkillCategory
from copy import copy


router = Router(tags=["Business Jobs"])

@router.get("employment-types", response=list[EmploymentTypeSchema])
def get_employment_types(request):
    employment_types = EmploymentType.objects.filter(parent=None)
    return employment_types


@router.post("create", response=CreateJobSchema)
def create_job(request, data:CreateJobSchema):
    response = copy(data)
    first_language = Language.objects.filter(uid=data.first_language_uid).first()
    for i in data.availability:
        available_day = AvailableDay(**i.dict())
    del data.availability
    return response


@router.get("departments", response=list[DepartmentSchema])
def get_departments(request):
    return Department.objects.all()


@router.get("roles", response=list[RoleSchema])
def get_roles(request):
    return Role.objects.all()


@router.get("skill-categories", response=list[SkillCategorySchema])
def get_skills(request):
    return SkillCategory.objects.all().prefetch_related("skill_set")
