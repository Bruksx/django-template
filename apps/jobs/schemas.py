from datetime import time, datetime
from decimal import Decimal
from typing import List
from typing import Optional
from uuid import UUID

from ninja import ModelSchema
from ninja.schema import Schema
from ninja_extra.schemas import PaginatedResponseSchema
from pydantic import Field, EmailStr

from accounts.enums import Days
from accounts.models import Department, Role, Skill, SkillCategory, Talent, BusinessUser
from core.schemas import READ_EXCLUDE_FIELDS, MUTATE_EXCLUDE_FIELDS, CountrySchema, EducationLevelSchema
from .enums import WorkStructureEnum, TechnologicalRequirementsEnum, LunchBreakEnum, QuestionTypeEnum, \
    WithdrawalFeedbackType, PhaseType, JobStatusType
from .models import BusinessModel, JobFilter, JobApplication
from .models import EmploymentType, Job, JobPost, ScreeningQuestion, QuestionOption, JobLevel, AvailableDay
from .models import (
    RequiredAttribute
)

class GenericNameAndUidSchema(Schema):
    uid: UUID
    name: str

class JobLevelSchema(ModelSchema):
    class Meta:
        model = JobLevel
        exclude = [*READ_EXCLUDE_FIELDS]

class BusinessModelSchema(ModelSchema):
    class Meta:
        model = BusinessModel
        exclude = [*READ_EXCLUDE_FIELDS]


class SkillSchema(ModelSchema):
    department: GenericNameAndUidSchema
    class Meta:
        model = Skill
        fields = ("uid",  "name")


class JobSkillSchema(Schema):
    category :str
    skills : List[SkillSchema]

class MutateJobAvailableDaySchema(ModelSchema):
    uid: Optional[UUID] = None
    active: Optional[bool] = True
    day: Days
    class Meta:
        model = AvailableDay
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job"]

class JobAvailableDaySchema(ModelSchema):
    class Meta:
        model = AvailableDay
        fields = ("uid", "start_time", "end_time")

class JobAvailabilitySchema(Schema):
    day: str
    availability: Optional[JobAvailableDaySchema] = None


class JobPostSchema(ModelSchema):
    country_uid: UUID

    class Meta:
        model = JobPost
        fields = ["province", "postal_code"]


class BusinessUserSchema(ModelSchema):
    name:str = Field(alias="user.fullname")
    email:EmailStr = Field(alias="user.email")
    class Meta:
        model = BusinessUser
        fields = ["uid", "role"]

class MutateJobPostSchema(ModelSchema):
    annual_bonus_currency_uid: Optional[UUID] = None
    annual_salary_currency_uid: Optional[UUID] = None
    status: Optional[JobStatusType] = None
    recruiter_uid: Optional[UUID] = None
    country_uid: Optional[UUID] = None
    class Meta:
        model = JobPost
        fields = ["province", "postal_code", "annual_salary_min", "annual_salary_max",
                  "annual_bonus_min", "annual_bonus_max"]

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
    availability: list[MutateJobAvailableDaySchema]
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


class JobPostDetailSchema(ModelSchema):
    annual_salary_min: float | None
    annual_salary_max: float | None
    annual_bonus_min: float | None
    annual_bonus_max: float | None
    annual_bonus_currency: str = ""
    annual_salary_currency: str = ""
    country: GenericNameAndUidSchema | None
    recruiter: Optional[BusinessUserSchema]


    class Meta:
        model = JobPost
        fields = ["uid", "province", "postal_code", "status"]

    @staticmethod
    def resolve_annual_bonus_currency(obj: JobPost):
        return obj.annual_bonus_currency.abbreviation

    @staticmethod
    def resolve_annual_salary_currency(obj: JobPost):
        return obj.annual_bonus_currency.abbreviation

class RequiredAttributeSchema(ModelSchema):
    business_model: list[BusinessModelSchema]
    skills: List[JobSkillSchema]

    class Meta:
        model = RequiredAttribute
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job", "uid", "skills"]

    @staticmethod
    def resolve_skills(obj):
        return obj.get_skills()


class JobDetailSchema(ModelSchema):
    uid: UUID
    logo_url: Optional[str]
    responsibilities: List[str]
    benefits: List[str]
    skills: List[JobSkillSchema]
    employment_type: Optional[GenericNameAndUidSchema]
    department: Optional[GenericNameAndUidSchema]
    job_level: Optional[GenericNameAndUidSchema]
    role: Optional[GenericNameAndUidSchema]
    business_models: List[GenericNameAndUidSchema]
    minimum_education_level: Optional[GenericNameAndUidSchema]
    availability: List[JobAvailabilitySchema]
    qualification: Optional[GenericNameAndUidSchema]
    first_language: Optional[GenericNameAndUidSchema]
    required_attribute: Optional[RequiredAttributeSchema]


    class Meta:
        model = Job
        fields = [
            "title", "hiring_company_name", "hiring_company_description", "about", "years_of_experience",
            "technological_requirement", "work_structure", "office_address","lunch_break",
            "additional_hours_min", "additional_hours_max",
            "share_compensation",
        ]
    
    @staticmethod
    def resolve_availability_timezone(obj):
        return str(obj.availability_timezone)

    @staticmethod
    def resolve_skills(obj):
        return obj.get_skills()
    
    @staticmethod
    def resolve_availability(obj):
        return obj.get_available_days()

    @staticmethod
    def resolve_required_attribute(obj):
        if not hasattr(obj, "requiredattribute"):
            return None
        return obj.requiredattribute



class JobPostListSchema(ModelSchema):
    role: Optional[str]
    client: str = Field(alias="job.hiring_company_name")
    location: str = Field(alias="country.name")
    applicants: int
    posted_by: Optional[str]

    class Meta:
        model = JobPost
        fields = ["uid", "status", "date_posted"]


    @staticmethod
    def resolve_role(obj):
        if not obj.job.role:
            return None
        return obj.job.role.name

    @staticmethod
    def resolve_applicants(obj):
        return obj.jobapplication_set.count()

    @staticmethod
    def resolve_posted_by(obj):
        if obj.posted_by:
            return obj.posted_by.user.fullname
        return None


class JobFullListSchema(ModelSchema):
    job_posts: List[JobPostListSchema]
    role: Optional[str]
    client:str = Field(alias="hiring_company_name")
    location: Optional[str]
    applicants:int
    posted_by: Optional[str]
    date_posted: datetime = Field(alias="created_at")
    status: Optional[str]

    class Meta:
        model = Job
        fields = ["uid",]

    @staticmethod
    def resolve_status(obj):
        value = JobFullListSchema.resolve_location(obj)
        if value not in ("Multiple", None):
            return obj.jobpost_set.first().status
        return None

    @staticmethod
    def resolve_job_posts(obj):
        return obj.jobpost_set

    @staticmethod
    def resolve_role(obj):
        if not obj.role:
            return None
        return obj.role.name

    @staticmethod
    def resolve_location(obj):
        job_posts= obj.jobpost_set
        if job_posts.count() == 0:
            return None
        elif job_posts.count() == 1:
            country = job_posts.first().country
            return country.name if country else None
        else:
            return "Multiple"

    @staticmethod
    def resolve_applicants(obj):
        return JobApplication.objects.filter(job_post__job=obj).count()

    @staticmethod
    def resolve_posted_by(obj):
        if obj.created_by:
            return obj.created_by.user.fullname
        return None


class JobListPaginatedSchema(PaginatedResponseSchema[JobFullListSchema]):
    roles: int
    posts: int

class JobPostWorkflowViewSchema(JobPostListSchema):
    screening: int
    interview: int
    onboarding: int
    hired: int
    rejected: int

    @staticmethod
    def resolve_screening(obj):
        return JobApplication.objects.filter(job_post=obj, stage__phase=PhaseType.SCREENING.value).count()

    @staticmethod
    def resolve_interview(obj):
        return JobApplication.objects.filter(job_post=obj, stage__phase=PhaseType.INTERVIEW.value).count()

    @staticmethod
    def resolve_onboarding(obj):
        return JobApplication.objects.filter(job_post=obj, stage__phase=PhaseType.ONBOARDING.value).count()

    @staticmethod
    def resolve_hired(obj):
        return JobApplication.objects.filter(job_post=obj, stage__phase=PhaseType.HIRED.value).count()

    @staticmethod
    def resolve_rejected(obj):
        return JobApplication.objects.filter(job_post=obj, stage__phase=PhaseType.REJECTED.value).count()

class JobFullWorkflowViewSchema(JobFullListSchema):
    job_posts: List[JobPostWorkflowViewSchema]
    screening: int
    interview: int
    onboarding: int
    hired: int
    rejected: int

    @staticmethod
    def resolve_screening(obj):
        return JobApplication.objects.filter(job_post__job=obj, stage__phase=PhaseType.SCREENING.value).count()

    @staticmethod
    def resolve_interview(obj):
        return JobApplication.objects.filter(job_post__job=obj, stage__phase=PhaseType.INTERVIEW.value).count()

    @staticmethod
    def resolve_onboarding(obj):
        return JobApplication.objects.filter(job_post__job=obj, stage__phase=PhaseType.ONBOARDING.value).count()

    @staticmethod
    def resolve_hired(obj):
        return JobApplication.objects.filter(job_post__job=obj, stage__phase=PhaseType.HIRED.value).count()

    @staticmethod
    def resolve_rejected(obj):
        return JobApplication.objects.filter(job_post__job=obj, stage__phase=PhaseType.REJECTED.value).count()

class JobWorkflowViewPaginatedSchema(PaginatedResponseSchema[JobFullWorkflowViewSchema]):
    roles: int
    posts: int


class JobApplicationCountSchema(Schema):
    key: str
    count: int


class JobPostFullDetailSchema(ModelSchema):
    applications: List[JobApplicationCountSchema]
    job: JobDetailSchema
    annual_salary_min: float
    annual_salary_max: float
    annual_bonus_min: float
    annual_bonus_max: float
    country: GenericNameAndUidSchema
    recruiter: Optional[BusinessUserSchema]
    posted_by: Optional[BusinessUserSchema]


    class Meta:
        model = JobPost
        fields = ["uid", "status", "date_posted",
                  "province", "postal_code"]


class MutateRequiredAttributeSchema(ModelSchema):
    skills: Optional[list[UUID]]
    business_model: Optional[list[UUID]]
    class Meta:
        model = RequiredAttribute
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job", "uid"]


class JobListSchema(ModelSchema):
    business_logo: Optional[str]
    business_name: str

    class Meta:
        model = Job
        fields = ["uid","title", "work_structure"]


class JobApplicationListSchema(ModelSchema):
    applicant_uid:UUID = Field(alias="applicant.uid")
    applicant:str = Field(alias="applicant.user.fullname")
    location:str = Field(alias="applicant.country.name")
    experience:int
    match:int
    phase:str
    stage:Optional[str] = None
    applicant_photo:Optional[str] = Field(alias="applicant.photo_url")
    class Meta:
        model = JobApplication
        fields = ("uid",  "created_at")

    @staticmethod
    def resolve_stage(obj):
        if not obj.stage:
            return
        return obj.stage.name

    @staticmethod
    def resolve_phase(obj):
        if not obj.stage:
            return "new"
        return obj.stage.phase

    @staticmethod
    def resolve_experience(obj):
        return int(obj.applicant.years_of_experience)



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


class TalentJobPostSchema(TalentJobPostListSchema):
    job: JobDetailSchema


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
