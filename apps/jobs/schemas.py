import logging
from datetime import time
from decimal import Decimal
from typing import List
from typing import Optional
from uuid import UUID

from ninja import ModelSchema
from ninja.schema import Schema
from pydantic import Field, EmailStr

from accounts.models import Department, Role, Skill, SkillCategory, Talent
from core.schemas import READ_EXCLUDE_FIELDS, MUTATE_EXCLUDE_FIELDS, CountrySchema, EducationLevelSchema
from .enums import WorkStructureEnum, TechnologicalRequirementsEnum, LunchBreakEnum, QuestionTypeEnum, \
    WithdrawalFeedbackType
from .models import BusinessModel, JobFilter, JobApplication
from .models import EmploymentType, Job, JobPost, ScreeningQuestion, QuestionOption, JobLevel, AvailableDay
from .models import (
    RequiredAttribute
)


class AvailabilitySchema(Schema):
    day: str
    start_time: time
    end_time: time


class JobPostSchema(ModelSchema):
    country_uid: UUID

    class Meta:
        model = JobPost
        fields = ["province", "postal_code"]


class MutateJobPostSchema(ModelSchema):
    annual_salary_min: float | None
    annual_salary_max: float | None
    annual_bonus_min: float | None
    annual_bonus_max: float | None
    annual_bonus_currency_uid: UUID
    annual_salary_currency_uid: UUID
    country_code: str
    class Meta:
        model = JobPost
        fields = ["uid", "province", "postal_code", "is_posted"]


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
    annual_salary_min: Decimal
    annual_salary_max: Decimal
    annual_bonus_min: Decimal
    annual_bonus_max: Decimal
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
        fields = ["uid", "name"]
    
    @staticmethod
    def resolve_category_name(obj):
        return obj.name
    
    @staticmethod
    def resolve_skills(obj, context):
        search = context.get("search")
        queryset = obj.skill_set.all()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return [SkillSchema.from_orm(skill) for skill in queryset]
    
class GenericNameAndUidSchema(Schema):
    uid: UUID
    name: str


class JobPostDetailSchema(ModelSchema):
    annual_salary_min: float | None
    annual_salary_max: float | None
    annual_bonus_min: float | None
    annual_bonus_max: float | None
    annual_bonus_currency: str = ""
    annual_salary_currency: str = ""
    country: GenericNameAndUidSchema | None

    class Meta:
        model = JobPost
        fields = ["uid", "province", "postal_code", "is_posted"]

    @staticmethod
    def resolve_annual_bonus_currency(obj: JobPost):
        return obj.annual_bonus_currency.abbreviation

    @staticmethod
    def resolve_annual_salary_currency(obj: JobPost):
        return obj.annual_bonus_currency.abbreviation



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


class MutateRequiredAttributeSchema(ModelSchema):
    skills: Optional[list[UUID]]
    business_model: Optional[list[UUID]]
    class Meta:
        model = RequiredAttribute
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job", "uid"]


class RequiredAttributeSkillCategory(ModelSchema):
    uid: UUID
    name: str
    skills: List[SkillSchema] = None

    class Meta:
        model = SkillCategory
        fields = ["uid", "name"]


class RequiredAttributeSchema(ModelSchema):
    business_model: list[BusinessModelSchema]
    skill_categories: list[RequiredAttributeSkillCategory]

    class Meta:
        model = RequiredAttribute
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job", "uid", "skills"]

    @staticmethod
    def resolve_skill_categories(obj):
        result = []
        for category in  SkillCategory.objects.all():
            skills = obj.skills.filter(category=category)
            category_json = RequiredAttributeSkillCategory(
                uid=category.uid,
                name=category.name,
                skills=skills
            )
            result.append(category_json)
        return result
class JobListSchema(ModelSchema):
    business_logo: Optional[str]
    business_name: str

    class Meta:
        model = Job
        fields = ["uid","title", "work_structure"]

class TalentJobPostListSchema(ModelSchema):
    job: JobListSchema
    match_score: Optional[int]

    class Meta:
        model = JobPost
        fields = ("uid", "job", "country", "province","postal_code")
        custom_fields = ("match_score",)

    @staticmethod
    def resolve_match_score(obj, context)->Optional[int]:
        request = context.get("request")
        user = request.user
        if not hasattr(user, "talent"):
            return None
        talent = user.talent
        score = talent.job_match_score(obj)
        return score

class MutateTalentJobFilterSchema(ModelSchema):
    location_type:WorkStructureEnum
    office_location: Optional[UUID]
    employment_type: Optional[UUID]
    department: Optional[UUID]
    minimum_education_level: Optional[UUID]

    class Meta:
        model = JobFilter
        fields = ["role", "years_of_experience", "location_type",  "remove_applied_jobs"]
        optional_fields = fields

class TalentJobFilterSchema(ModelSchema):
    location_type: Optional[WorkStructureEnum]
    office_location: Optional[CountrySchema]
    employment_type: Optional[EmploymentTypeSchema]
    department: Optional[DepartmentSchema]
    minimum_education_level: Optional[EducationLevelSchema]

    class Meta:
        model = JobFilter
        fields = ["role", "years_of_experience", "location_type",  "remove_applied_jobs"]
        optional_fields = fields



class TalentJobApplySchema(ModelSchema):
    class Meta:
        model = JobApplication
        fields = ("accept_privacy", "is_available")

class TalentJobApplicationWithdrawalSchema(Schema):
       feedback_type: WithdrawalFeedbackType
       feedback: str

class ShareJobPostViaEmailSchema(Schema):
    emails: List[str]


class ShareJobPostViaChatSchema(Schema):
    talent_ids: List[UUID]

class TalentListJobPostSchema(ModelSchema):
    first_name: str = Field(alias="user.first_name")
    last_name: str = Field(alias="user.last_name")
    user_uid: UUID = Field(alias="user.uid")
    email: EmailStr = Field(alias="user.email")
    phone_number: Optional[str] = Field(alias="user.phone_number")
    photo_url: Optional[str]
    match_score: Optional[int]

    class Meta:
        model = Talent
        fields = ("uid",)

    @staticmethod
    def resolve_match_score(obj, context)->Optional[int]:
        request = context.get("request")
        job_post = request.context.get("job_post")
        score = obj.job_match_score(job_post)
        return score
