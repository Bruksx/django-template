from datetime import time
from typing import List
from typing import Optional
from uuid import UUID

from ninja import ModelSchema
from ninja.schema import Schema

from accounts.models import Department, Role, Skill, SkillCategory
from core.schemas import READ_EXCLUDE_FIELDS
from .enums import WorkStructureEnum, TechnologicalRequirementsEnum, LunchBreakEnum, QuestionTypeEnum
from .models import BusinessModel
from .models import EmploymentType, Job, JobPost, ScreeningQuestion, QuestionOption, JobLevel, AvailableDay


class AvailabilitySchema(Schema):
    day: str
    start_time: time
    end_time: time


class JobPostSchema(ModelSchema):
    country_code: str

    class Meta:
        model = JobPost
        fields = ["province", "postal_code"]


class QuestionOptionSchema(ModelSchema):
    class Meta:
        model = QuestionOption
        fields = ["is_accepted", "text"]


class QuestionSchema(ModelSchema):
    type: QuestionTypeEnum
    options: List[QuestionOptionSchema]

    class Meta:
        model = ScreeningQuestion
        fields = ["type", "text", "is_knockout"]


class CreateJobSchema(Schema):
    title: str
    employment_type_uid: UUID
    availability: list[AvailabilitySchema]
    work_structure: WorkStructureEnum
    technological_requirements: TechnologicalRequirementsEnum
    first_language_uid: UUID
    additional_languages: List[UUID]
    lunch_break: LunchBreakEnum
    job_posts: List[JobPostSchema]
    recruiter_uid: UUID
    annual_salary_min: float
    annual_salary_max: float
    annual_bonus_min: float
    annual_bonus_max: float
    same_recruiter: bool
    screening_questions: List[QuestionSchema]
    department_uid: UUID
    role_uid: UUID
    skills: list[UUID]
    job_level_uid: Optional[UUID]

    class Meta:
        model = Job
        fields = [
            "hiring_company_name", "hiring_company_description", "work_structure", "office_address","lunch_break", 
            "additional_hours_min", "additional_hours_max", "annual_salary_min", "annual_salary_max",
            "annual_salary_currency", "annual_bonus_min", "annual_bonus_max", "annual_bonus_currency", "benefits",
            "share_compensation", 
        ]
        fields_optional = fields


class EmploymentSubTypeSchema(Schema):
    uid: UUID
    name: str


class EmploymentTypeSchema(Schema):
    uid: UUID
    name: str
    sub_types: List[EmploymentSubTypeSchema]
    
    @staticmethod
    def resolve_sub_types(obj):
        return EmploymentType.objects.filter(parent=obj)


class DepartmentSchema(ModelSchema):
    class Meta:
        model = Department
        fields = ["uid", "name"]


class RoleSchema(ModelSchema):
    class Meta:
        model = Role
        fields = ["uid", "name"]


class SkillSchema(ModelSchema):
    class Meta:
        model = Skill
        fields = ["uid", "name"]


class SkillCategorySchema(Schema):
    uid: UUID
    category_name: str
    skills: List[SkillSchema]

    class Meta:
        model = SkillCategory
        fields = ["uid", "name", "skills"]
    
    @staticmethod
    def resolve_category_name(obj):
        return obj.name
    
    """@staticmethod
    def resolve_skills(obj):
        return Skill.objects.filter(category=obj)"""
    
class GenericNameAndUidSchema(Schema):
    uid: UUID
    name: str


class JobPostDetailSchema(Schema):
    annual_salary_min: float | None
    annual_salary_max: float | None
    annual_bonus_min: float | None
    annual_bonus_max: float | None
    class Meta:
        model = JobPost
        fields = ["uid", "province", "postal_code", "is_posted", "annual_salary_currency", "annual_bonus_currency"]


class JobDetailSchema(Schema):
    uid: UUID
    annual_salary_min: float
    annual_salary_max: float
    annual_bonus_min: float
    annual_bonus_max: float
    employment_type: GenericNameAndUidSchema
    availability: list[AvailabilitySchema]
    job_posts: list[JobPostDetailSchema]

    class Meta:
        model = Job
        fields = [
            "title", "hiring_company_name", "hiring_company_description", "work_structure", "office_address","lunch_break",
            "additional_hours_min", "additional_hours_max", "annual_salary_min", "annual_salary_max",
            "annual_salary_currency", "annual_bonus_min", "annual_bonus_max", "annual_bonus_currency", "benefits",
            "share_compensation", "employment_type"
        ]
    
    @staticmethod
    def resolve_availability_timezone(obj):
        return str(obj.availability_timezone)
    
    @staticmethod
    def resolve_availability(obj):
        return AvailableDay.objects.filter(job=obj)

    @staticmethod
    def resolve_job_posts(obj):
        return JobPost.objects.filter(job=obj)
    
class JobLevelSchema(ModelSchema):
    class Meta:
        model = JobLevel
        exclude = [*READ_EXCLUDE_FIELDS]


class BusinessModelSchema(ModelSchema):
    class Meta:
        model = BusinessModel
        exclude = [*READ_EXCLUDE_FIELDS]