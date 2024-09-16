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
    data_dict = data.dict()
    first_language = Language.objects.filter(uid=data.first_language_uid).first()
    employment_type = EmploymentType.objects.filter(uid=data.employment_type_uid).first()
    department = Department.objects.filter(uid=data.department_uid).first()
    role = Role.objects.filter(uid=data.role_uid).first()
    job_level = JobLevel.objects.filter(uid=data.job_level_uid).first()
    recruiter = User.objects.filter(uid=data.recruiter_uid).first()

    to_be_deleted = [
        "employment_type_uid", "first_language_uid", "role_uid", "job_level_uid","additional_languages", "skills", 
        "availability", "technological_requirements", "job_posts", "recruiter_uid", "same_recruiter", "screening_questions", 
        "department_uid", "work_structure", "lunch_break",
    ]
    for attr in to_be_deleted:
        del data_dict[attr]
    job = Job(**data_dict)
    job.created_by = request.user
    job.business = business_user.business
    job.first_language = first_language
    job.department = department
    job.employment_type = employment_type
    job.role = role
    job.job_level = job_level
    job.recruiter = recruiter
    job.save()

    for i in data.availability:
        available_day = AvailableDay(job=job, **i.dict())
        available_day.save()
    for i in data.job_posts:
        country = Country.objects.filter(code=i.country_code).first()
        post = JobPost(
            job=job,
            country=country,
            province=i.province,
            postal_code=i.postal_code,
        )
        if data.same_recruiter:
            post.recruiter = recruiter
        post.save()
    for i in data.screening_questions:
        question = ScreeningQuestion(
            job=job,
            type=i.type.value,
            text=i.text,
            is_knockout=i.is_knockout,
        )
        question.save()
        for option in i.options:
            question_option = QuestionOption(
                question=question,
                is_accepted=option.is_accepted,
                text=option.text,
            )
            question_option.save()
    skills = Skill.objects.filter(uid__in=data.skills)
    job.skills.add(*skills)
    return job