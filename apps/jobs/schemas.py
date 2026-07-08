from copy import copy
from datetime import datetime
from typing import List, Literal, Any, Dict
from typing import Optional
from uuid import UUID

from django.db.models import QuerySet, Q, Count, Exists, OuterRef
from django.utils import timezone
from ninja import ModelSchema
from ninja.errors import HttpError
from ninja.schema import Schema
from pydantic import Field, EmailStr

from accounts.enums import Days
from accounts.models import Department, Role, Skill, SkillCategory, Talent, BusinessUser
from accounts.schemas.business import BusinessUserListSchema
from ai.models import AIApplicationInsight, AIMatchScore
from core.enums import SalaryType
from core.models import Currency
from core.schemas import READ_EXCLUDE_FIELDS, MUTATE_EXCLUDE_FIELDS, EducationLevelSchema
from helpers.utils import export_rows_to_excel
from paginations import CustomPaginatedResponseSchema as PaginatedResponseSchema
from settings.models import WorkFlowStage
from .enums import WorkStructureEnum, TechnologicalRequirementsEnum, LunchBreakEnum, QuestionTypeEnum, \
    WithdrawalFeedbackType, JobStatusType, ActionType, PhaseType, UpdateQuickReviewType, RejectionReasonType
from .models import BusinessModel, JobApplication, Answer, JobInvite, JobApplicationNotes
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


class MutateJobPostSchema(ModelSchema):
    country: Optional[UUID] = None
    city: Optional[str] = None
    province: Optional[UUID] = None
    benefits: List[str]
    recruiter: Optional[UUID] = None
    status: Optional[JobStatusType] = None
    salary_currency: Optional[UUID] = None
    salary_bonus_currency: Optional[UUID] = None
    salary_type: Optional[SalaryType] = None
    salary_bonus_type: Optional[SalaryType] = None
    tags: List[str] = []
    linkedin_tags: List[str] = []



    class Meta:
        model = JobPost
        exclude = [*MUTATE_EXCLUDE_FIELDS, "uid", "job", "created_at", "posted_by", "date_posted"]
        fields_optional = "__all__"

class UpdateJobPostSchema(ModelSchema):
    country: Optional[UUID] = None
    city: Optional[str] = None
    province: Optional[UUID] = None
    uid: Optional[UUID] = None
    benefits: List[str]
    recruiter: Optional[UUID] = None
    status: Optional[JobStatusType] = None
    salary_currency: Optional[UUID] = None
    salary_type: Optional[SalaryType] = None
    salary_bonus_type: Optional[SalaryType] = None
    salary_bonus_currency: Optional[UUID] = None
    tags: List[str] = []
    linkedin_tags: List[str] = []
    
    
    class Meta:
        model = JobPost
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job", "created_at", "posted_by", "date_posted"]
        fields_optional = "__all__"


class MutateJobPostListSchema(ModelSchema):
    country: Optional[GenericNameAndUidSchema] = None
    city: Optional[str] = None
    province: Optional[GenericNameAndUidSchema] = None
    recruiter: Optional[BusinessUserListSchema]
    benefits: List[str]
    status: Optional[str]
    salary_bonus_currency: Optional[GenericNameAndUidSchema]
    salary_currency: Optional[GenericNameAndUidSchema]
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_bonus_min: Optional[float]
    salary_bonus_max: Optional[float]
    salary_type: Optional[SalaryType] = None
    salary_bonus_type: Optional[SalaryType] = None
    tags: List[str] = Field(alias="get_tags")
    linkedin_tags: List[str]
    code: str = Field(alias="get_code")
    about: Optional[str] = Field(None, alias="get_about")
    

    class Meta:
        model = JobPost
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job", "created_at", "posted_by", "date_posted"]
        fields_optional = "__all__"

class BusinessUserSchema(ModelSchema):
    name:str = Field(alias="user.fullname")
    email:EmailStr = Field(alias="user.email")
    class Meta:
        model = BusinessUser
        fields = ["uid", "role"]

class CreateQuestionOptionSchema(ModelSchema):
    class Meta:
        model = QuestionOption
        fields = ["is_accepted", "text"]



class CreateQuestionSchema(ModelSchema):
    type: QuestionTypeEnum
    options: List[CreateQuestionOptionSchema]

    class Meta:
        model = ScreeningQuestion
        fields = ["type", "text", "is_knockout"]


class QuestionOptionSchema(ModelSchema):

    class Meta:
        model = QuestionOption
        fields = ["uid", "is_accepted", "text"]

class TalentQuestionOptionSchema(ModelSchema):
    class Meta:
        model = QuestionOption
        fields = ["uid", "text"]

class QuestionSchema(ModelSchema):
    type: QuestionTypeEnum
    options: List[QuestionOptionSchema]

    class Meta:
        model = ScreeningQuestion
        fields = ["uid", "type", "text", "is_knockout"]

class TalentQuestionSchema(ModelSchema):
    type: QuestionTypeEnum
    options: List[TalentQuestionOptionSchema]

    class Meta:
        model = ScreeningQuestion
        fields = ["uid", "type", "text", "is_knockout"]

class UpdateQuestionSchema(ModelSchema):
    type: Optional[QuestionTypeEnum] = None
    class Meta:
        model = ScreeningQuestion
        fields = ["type", "text", "is_knockout"]

class MutateOptionSchema(ModelSchema):
    uid: Optional[UUID] = None
    class Meta:
        model = QuestionOption
        fields = ["is_accepted", "text"]


class MutateQuestionSchema(ModelSchema):
    uid: Optional[UUID] = None
    type: Optional[QuestionTypeEnum] = None
    options: List[MutateOptionSchema] = None

    class Meta:
        model = ScreeningQuestion
        fields = ["type", "text", "is_knockout"]


class ScreeningAnswerSchema(ModelSchema):
    question: QuestionSchema
    options: Optional[List[QuestionOptionSchema]] = None
    text: Optional[str] = None
    files : Optional[List[str]] = None

    class Meta:
        model = Answer
        fields = ["uid"]

class MutateAnswerSchema(Schema):
    question: UUID
    options: Optional[List[UUID]] = None
    text: Optional[str] = None
    files: Optional[List[str]] = None


class MutateRequiredAttributeSchema(ModelSchema):
    skills: Optional[list[UUID]]
    business_models: Optional[list[UUID]] = list()
    secondary_languages: Optional[list[UUID]] = list()
    class Meta:
        model = RequiredAttribute
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job", "uid"]

    @classmethod
    def validate_required_attribute(cls, data: dict, job):
        data = copy(data)
        count = 0
        many_to_many_fields = ["skills", "business_models", "secondary_languages",]
        for field in many_to_many_fields:
            count += len(data.pop(field, []))
        for field in data.keys():
            value = data[field]
            if value == True:
                count += 1
        if count > 5:
            raise HttpError(400, "You can only add up to 5 required attributes")


class MutatePutRequiredAttributeSchema(MutateRequiredAttributeSchema):
    skills: list[UUID]
    business_models: list[UUID]
    secondary_languages: list[UUID]
    job_level: bool
    years_of_experience: bool
    minimum_education_level: bool
    work_structure: bool
    technological_requirement: bool
    first_language: bool
    secondary_language: bool
    working_hours: bool
    location: bool
    class Meta:
        model = RequiredAttribute
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job", "uid"]


class CreateJobSchema(ModelSchema):
    employment_type: UUID
    availability: list[MutateJobAvailableDaySchema]
    work_structure: WorkStructureEnum
    technological_requirement: TechnologicalRequirementsEnum
    first_language: UUID
    additional_languages: List[UUID]
    lunch_break: LunchBreakEnum
    job_posts: List[MutateJobPostSchema]
    screening_questions: List[CreateQuestionSchema]
    #department: UUID
    role: UUID
    skills: list[UUID]
    job_level: Optional[UUID]
    business_models: List[UUID]
    minimum_education_level: UUID
    responsibilities: Optional[str] = ""
    min_match_score: Optional[float] = None
    required_attributes: Optional[MutateRequiredAttributeSchema] = None


    class Meta:
        model = Job
        exclude = [
            *MUTATE_EXCLUDE_FIELDS, "business_models", "created_by","uid"]
        fields_optional = "__all__"

class JobLogoSchema(Schema):
    base64: str
    content_type: Literal['image/jpg', 'image/png', 'image/jpeg', 'image/gif']
    name: Optional[str] = None


    def get_name(self):
        if not self.name:
            self.name = f"job-logo-{str(timezone.now().timestamp()).split('.')[0]}"
        name = str(self.name).strip().replace(" ", "-")
        content_type = self.content_type.split("/")[-1] if "/" in self.content_type else self.content_type
        return name if name.split(".")[-1] in ("jpg", "jpeg", "gif", "png") else f"{name}.{content_type}"

class OptionalCreateJobSchema(ModelSchema):
    employment_type: Optional[UUID] = None
    availability: Optional[List[MutateJobAvailableDaySchema]] = None
    work_structure: Optional[WorkStructureEnum] = None
    technological_requirement: Optional[TechnologicalRequirementsEnum] = None
    first_language: Optional[UUID] = None
    additional_languages: Optional[List[UUID]] = None
    job_posts: List[MutateJobPostSchema]
    screening_questions: List[CreateQuestionSchema]
    lunch_break: Optional[LunchBreakEnum] = None
    department: Optional[UUID] = None
    role: Optional[UUID] = None
    skills: Optional[List[UUID]] = None
    job_level: Optional[UUID] = None
    logo: Optional[JobLogoSchema] = None
    business_models: Optional[List[UUID]] = None
    minimum_education_level: Optional[UUID] = None
    responsibilities: Optional[str] = ""
    min_match_score: Optional[float] = None
    required_attributes: Optional[MutateRequiredAttributeSchema] = None
    additional_hours_start: Optional[str] = None
    additional_hours_end: Optional[str] = None

    class Meta:
        model = Job
        exclude = [
            *MUTATE_EXCLUDE_FIELDS, "role", "first_language", "job_level", "department",
             "business_models", "created_by", "employment_type", "minimum_education_level",
            "uid"
        ]
        fields_optional = "__all__"

class UpdateJobSchema(ModelSchema):
    employment_type: Optional[UUID] = None
    availability: Optional[List[MutateJobAvailableDaySchema]] = None
    work_structure: Optional[WorkStructureEnum] = None
    technological_requirement: Optional[TechnologicalRequirementsEnum] = None
    first_language: Optional[UUID] = None
    additional_languages: List[UUID]
    lunch_break: Optional[LunchBreakEnum] = None
    department: Optional[UUID] = None
    role: Optional[UUID] = None
    skills: List[Optional[UUID]] = None
    job_level: Optional[UUID] = None
    logo: Optional[JobLogoSchema] = None
    business_models: Optional[List[UUID]] = None
    minimum_education_level: Optional[UUID] = None
    responsibilities: Optional[str] = ""
    min_match_score: Optional[float] = None
    required_attributes: Optional[MutateRequiredAttributeSchema] = None
    additional_hours_start: Optional[str] = None
    additional_hours_end: Optional[str] = None
    job_posts : List[UpdateJobPostSchema]  = []
    screening_questions: List[MutateQuestionSchema]

    class Meta:
        model = Job
        exclude = [
            *MUTATE_EXCLUDE_FIELDS, "role", "first_language", "job_level", "department",
             "business_models", "created_by", "employment_type", "minimum_education_level",
            "uid"
        ]
        fields_optional = "__all__"

class EmploymentSubTypeSchema(Schema):
    uid: UUID
    name: str


class EmploymentParentTypeSchema(Schema):
    uid: UUID
    name: str
    sub_types: List[EmploymentSubTypeSchema]
    
    @staticmethod
    def resolve_sub_types(obj):
        return EmploymentType.objects.filter(parent=obj)


class EmploymentTypeSchema(Schema):
    uid: UUID
    name: str  = Field(alias="fullname")



class DepartmentSchema(ModelSchema):
    class Meta:
        model = Department
        fields = ["uid", "name"]

    @staticmethod
    def resolve_name(obj, context):
        if hasattr(obj, 'fullname'):
            return obj.fullname
        return obj.name


class RoleSchema(ModelSchema):
    class Meta:
        model = Role
        fields = ["uid", "name"]

    @staticmethod
    def resolve_name(obj, context):
        if hasattr(obj, 'fullname'):
            return obj.fullname
        return obj.name

class AddRoleSchema(Schema):
    department: UUID
    role: str

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
        department = context.get("department")
        queryset = obj.skill_set.all()
        if search:
            queryset = queryset.filter(name__icontains=search)
        if department:
            queryset = queryset.filter(department__uid=department)

        queryset = queryset.distinct("name").order_by("name")
        return [SkillSchema.from_orm(skill) for skill in queryset.iterator()]


class JobPostDetailSchema(ModelSchema):
    country: GenericNameAndUidSchema | None
    recruiter: Optional[BusinessUserSchema]
    benefits: List[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_bonus_min: Optional[float]
    salary_bonus_max: Optional[float]
    salary_bonus_currency: Optional[str] = None
    salary_currency: Optional[str] = None
    saved: Optional[bool]
    alert: Optional[bool]
    applied: Optional[bool]
    city: str | None
    province: GenericNameAndUidSchema | None
    about: Optional[str] = Field(None, alias="get_about")
    tags: List[str] = Field(alias="get_tags")
    linkedin_tags: List[str]
    code: str = Field(alias="get_code")
    

    class Meta:
        model = JobPost
        fields = ["uid",  "postal_code", "status", "promotion_code", "share_compensation", "created_at", "date_posted", "salary_type", "salary_bonus_type"]

    @staticmethod
    def resolve_salary_bonus_currency(obj):
        if obj.salary_bonus_currency:
            return obj.salary_bonus_currency.abbreviation
        return

    @staticmethod
    def resolve_applied(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return None
        return JobApplication.objects.filter(job_post=obj, applicant=talent).exists()

    @staticmethod
    def resolve_alert(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return
        if not hasattr(talent, "jobalert"):
            return False
        return talent.jobalert.jobs.filter(id=obj.job_id).exists()

    @staticmethod
    def resolve_saved(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return
        return talent.savedjob_set.filter(job_post=obj).exists()

    @staticmethod
    def resolve_salary_currency(obj):
        if obj.salary_currency:
            return obj.salary_currency.abbreviation
        return

class RequiredAttributeSchema(ModelSchema):
    business_models: list[BusinessModelSchema]
    skills: List[JobSkillSchema]

    class Meta:
        model = RequiredAttribute
        exclude = [*MUTATE_EXCLUDE_FIELDS, "job"]

    @staticmethod
    def resolve_skills(obj):
        return obj.get_skills()

class JobListSchema2(ModelSchema):
    uid: UUID
    logo_url: Optional[str]
    role: Optional[GenericNameAndUidSchema]
    title: str = Field(alias="get_title")
    hiring_company_name: Optional[str] = Field(alias="hiring_company")
    business_name: Optional[str] = None

    class Meta:
        model = Job
        fields = ["work_structure", "office_address", "cv_required"]



class JobDetailSchema(ModelSchema):
    uid: UUID
    logo_url: Optional[str]
    responsibilities: Optional[str] = ""
    skills: List[JobSkillSchema]
    employment_type: Optional[EmploymentTypeSchema]
    department: Optional[GenericNameAndUidSchema]
    job_level: Optional[GenericNameAndUidSchema]
    role: Optional[GenericNameAndUidSchema]
    business_models: List[GenericNameAndUidSchema]
    minimum_education_level: Optional[EducationLevelSchema]
    availability: List[JobAvailabilitySchema]
    first_language: Optional[GenericNameAndUidSchema]
    additional_languages: List[GenericNameAndUidSchema]
    required_attribute: Optional[RequiredAttributeSchema]
    title:Optional[str] = Field(alias="get_title")
    business_name : Optional[str] = None

    class Meta:
        model = Job
        fields = [
            "hiring_company_name", "hiring_company_description", "about", "years_of_experience",
            "technological_requirement", "work_structure", "office_address","lunch_break", "lunch_break_time",
            "additional_hours_start", "additional_hours_end", "flexible_availability", "qualification",
            "availability_timezone", "additional_hours_description", "additional_skills", "cv_required"
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



class JobMatchSchema(Schema):
    skills: Optional[List[JobSkillSchema]] = None
    job_level: Optional[GenericNameAndUidSchema] = None
    role: Optional[GenericNameAndUidSchema] = None
    business_models: Optional[List[GenericNameAndUidSchema]] = None
    minimum_education_level: Optional[EducationLevelSchema] = None
    work_structure: Optional[WorkStructureEnum] = None
    years_of_experience: Optional[int] = None
    first_language: Optional[GenericNameAndUidSchema] = None
    secondary_language: Optional[List[GenericNameAndUidSchema]] = None
    location: Optional[GenericNameAndUidSchema] = None
    working_hours: Optional[List[JobAvailabilitySchema]] = None


class JobPostListSchema(ModelSchema):
    role: Optional[str]
    client: str = Field(alias="job.hiring_company_name")
    business_name : Optional[str] = Field(None, alias="job.business_name")
    location: Optional[str] = Field(None, alias="get_country")
    applicants: int
    posted_by: Optional[str]
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_bonus_min: Optional[float] = None
    salary_bonus_max: Optional[float] = None
    salary_bonus_currency: Optional[str]
    salary_currency: Optional[str]
    alert: Optional[bool] = None
    applied: Optional[bool]= None
    saved: Optional[bool] = None
    recruiter: Optional[str] = None
    city: Optional[str] = Field(None, alias="get_city")
    province: Optional[str] = Field(None, alias="get_province")
    about: Optional[str] = Field(None, alias="get_about")
    tags: List[str] = Field(alias="get_tags")
    linkedin_tags: List[str]
    code: str = Field(alias="get_code")
    


    class Meta:
        model = JobPost
        fields = ["uid", "status", "created_at", "promotion_code", "date_posted", "share_compensation", "last_refreshed", "salary_type", "salary_bonus_type"]


    @staticmethod
    def resolve_role(obj):
        if not obj.job.role:
            return None
        return obj.job.role.name

    @staticmethod
    def resolve_recruiter(obj):
        recruiter = obj.recruiter
        if not recruiter:
            return None
        return recruiter.user.fullname

    @staticmethod
    def resolve_applied(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return None
        return JobApplication.objects.filter(job_post=obj, applicant=talent).exists()

    @staticmethod
    def resolve_saved(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return None
        return talent.savedjob_set.filter(job_post=obj).exists()

    @staticmethod
    def resolve_alert(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return
        if not hasattr(talent, "jobalert"):
            return False
        return talent.jobalert.jobs.filter(id=obj.job_id).exists()

    @staticmethod
    def resolve_applicants(obj):
        return obj.jobapplication_set.count()

    @staticmethod
    def resolve_posted_by(obj):
        if obj.posted_by:
            return obj.posted_by.user.fullname
        return None

    @staticmethod
    def resolve_salary_bonus_currency(obj):
        if obj.salary_bonus_currency:
            return obj.salary_bonus_currency.abbreviation
        return

    @staticmethod
    def resolve_salary_currency(obj):
        if obj.salary_currency:
            return obj.salary_currency.abbreviation
        return


class JobFullListSchema(ModelSchema):
    job_posts: List[JobPostListSchema]
    role: Optional[str]
    logo_url: Optional[str]
    client:str = Field(alias="hiring_company_name")
    business_name : Optional[str] = None
    location: Optional[str]
    applicants:int
    posted_by: Optional[str]
    date_posted: Optional[datetime] = None
    status: Optional[str]
    recruiter: Optional[str]

    class Meta:
        model = Job
        fields = ["uid",  "cv_required"]

    @staticmethod
    def resolve_status(obj):
        if obj.jobpost_set.count() == 0:
            return None
        elif obj.jobpost_set.count() == 1:
            return obj.jobpost_set.first().status
        return "Multiple"

    @staticmethod
    def resolve_recruiter(obj):
        count = obj.jobpost_set.count()
        if count == 0:
            return None
        elif count == 1:
            recruiter = obj.jobpost_set.first().recruiter
            if not recruiter:
                return None
            return recruiter.user.fullname
        return "Multiple"

    @staticmethod
    def resolve_job_posts(obj, context):
        queryset = obj.jobpost_set
        request = context.get("request")
        if request and hasattr(request, "context"):
            context = request.context
        else:
            context = dict()
        return BusinessJobFilterSchema.filter_job_posts(context, queryset).order_by("-refresh_order", "-posted_order")

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
        return JobApplication.objects.select_related("job_post__job").filter(job_post__job=obj).count()

    @staticmethod
    def resolve_posted_by(obj):
        if obj.created_by:
            return obj.created_by.user.fullname
        return None

class FullJobDetailSchema(JobDetailSchema, JobFullListSchema):
    job_posts: List[MutateJobPostListSchema]
    @staticmethod
    def resolve_role(obj):
        if not obj.role:
            return None
        return obj.role

class JobListPaginatedSchema(PaginatedResponseSchema[JobFullListSchema]):
    roles: int
    posts: int

class WorkFlowSchema(ModelSchema):
    uid: UUID
    applications: int
    phase: PhaseType

    class Meta:
        model = WorkFlowStage
        fields = ("uid", "phase", "name")

class JobPostWorkflowViewSchema(JobPostListSchema):
    workflow_data: List[WorkFlowSchema]

    @staticmethod
    def resolve_workflow_data(obj):
        return obj.workflow_stage_data()

class JobFullWorkflowViewSchema(JobFullListSchema):
    job_posts: List[JobPostWorkflowViewSchema]

    workflow_data: List[WorkFlowSchema]


    @staticmethod
    def resolve_workflow_data(obj, context):
        return obj.workflow_stage_data()

    def export_to_excel(self):
        return export_rows_to_excel(self)

class JobWorkflowViewPaginatedSchema(PaginatedResponseSchema[JobFullWorkflowViewSchema]):
    roles: int
    posts: int


class JobApplicationCountSchema(Schema):
    key: str
    count: int


class JobPostFullDetailSchema(ModelSchema):
    workflow_data: List[WorkFlowSchema]
    applicants: int
    withdrawals: int
    job: JobDetailSchema
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_bonus_min: Optional[float] = None
    salary_bonus_max: Optional[float] = None
    salary_bonus_currency: Optional[str] = None
    salary_currency: Optional[str] = None
    country: Optional[GenericNameAndUidSchema] = None
    recruiter: Optional[BusinessUserSchema]
    posted_by: Optional[BusinessUserSchema]
    edited_by: Optional[BusinessUserSchema]
    benefits: List[str] = list()
    saved: Optional[bool] = None
    alert: Optional[bool] = None
    city: Optional[str] = None
    province: Optional[GenericNameAndUidSchema] = None
    about: Optional[str] = Field(None, alias="get_about")
    tags: List[str] = Field(alias="get_tags")
    linkedin_tags: List[str]
    code: str = Field(alias="get_code")
    


    class Meta:
        model = JobPost
        fields = ["uid", "status", "created_at",  "postal_code", "date_posted",
                  "share_compensation", "salary_type", "salary_bonus_type", "edited_at", "promotion_code"]

    @staticmethod
    def resolve_saved(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return
        return talent.savedjob_set.filter(job_post=obj).exists()

    @staticmethod
    def resolve_applicants(obj):
        return obj.jobapplication_set.count()
    
    @staticmethod
    def resolve_withdrawals(obj):
        return obj.jobapplicationwithdrawal_set.count()

    @staticmethod
    def resolve_workflow_data(obj, context):
        return obj.workflow_stage_data()

    @staticmethod
    def resolve_alert(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return
        if not hasattr(talent, "jobalert"):
            return False
        return talent.jobalert.jobs.filter(id=obj.job_id).exists()

    @staticmethod
    def resolve_salary_bonus_currency(obj):
        if obj.salary_bonus_currency:
            return obj.salary_bonus_currency.abbreviation
        return

    @staticmethod
    def resolve_salary_currency(obj):
        if obj.salary_currency:
            return obj.salary_currency.abbreviation
        return



class JobListSchema(ModelSchema):
    business_logo: Optional[str]
    business_name: str
    role: Optional[GenericNameAndUidSchema]
    title: Optional[str] = Field(alias="get_title")

    class Meta:
        model = Job
        fields = ["uid","work_structure", "role", "cv_required"]

class OtherApplicationSchema(ModelSchema):
    job_logo: Optional[str] = Field(None, alias="job_post.job.business_logo")
    job_company: Optional[str] = Field(None, alias="job_post.job.business_name")
    role: Optional[GenericNameAndUidSchema] = Field(alias="job_post.job.role")
    location: Optional[GenericNameAndUidSchema] = Field(alias="job_post.country")
    job_stage: Optional[str]
    invited: bool
    applied_date: datetime = Field(alias="created_at")
    recruiter: Optional[BusinessUserSchema] = Field(alias="job_post.recruiter")
    job_status: str

    class Meta:
        model = JobApplication
        fields = ("uid",)

    @staticmethod
    def resolve_job_stage(obj):
        if not obj.stage:
            return
        return obj.stage.name

    @staticmethod
    def resolve_job_status(obj):
        return "Active" if obj.job_post.status == JobStatusType.POSTED.value else "Closed"


class AIInsightSchema(Schema):
    summary: Optional[str] = None
    strength: Optional[list[str]] = []
    weaknesses: Optional[list[str]] = []
    red_flags: Optional[list[Dict[str, Any]]] = []


class JobApplicationListSchema(ModelSchema):
    job_role: Optional[GenericNameAndUidSchema] = Field(alias="job_post.job.role")
    location:Optional[str] = Field(None, alias="job_post.get_country")
    role:Optional[GenericNameAndUidSchema] = Field(alias="applicant.get_role")
    experience:int
    match:int
    phase:str
    stage:Optional[str] = None
    stage_uid:Optional[UUID] = None
    applicant_uid: UUID = Field(alias="applicant.uid")
    applicant: str = Field(alias="applicant.user.fullname")
    applicant_location: Optional[str] = Field(None, alias="applicant.get_country")
    applicant_photo:Optional[str] = Field(alias="applicant.photo_url")
    applicant_email: str = Field(alias="applicant.user.email")
    applicant_user_uid: UUID = Field(alias="applicant.user.uid")
    applicant_phone: Optional[str] = Field(alias="applicant.user.get_phone")
    applicant_country: Optional[GenericNameAndUidSchema] = Field(alias="applicant.country")
    applicant_cv_url: Optional[str]
    applicant_job_type: Optional[str] = Field(default=None, alias="applicant.job_type")

    applicant_linkedin_url: Optional[str] = Field(alias="applicant.linkedin")
    years_of_experience: str = Field(alias="applicant.get_years_of_experience")
    average_experience_tenure: str = Field(alias="applicant.get_average_experience_tenure")
    other_application: Optional[OtherApplicationSchema]
    recruiter: Optional[BusinessUserSchema] = Field(alias="job_post.recruiter")
    job_status: str
    invited: bool
    ai_insight: AIInsightSchema
    ai_match_score: Optional[int] = None
    top_percent: Optional[int] = None
    rank: Optional[int] = 0
    pool_size: Optional[int] = 0

    class Meta:
        model = JobApplication
        fields = ("uid",  "created_at", "available_for_schedule")

    @staticmethod
    def resolve_applicant_cv_url(obj):
        return obj.applicant.cv_url

    @staticmethod
    def resolve_job_status(obj):
        return "Active" if obj.job_post.status == JobStatusType.POSTED.value else "Closed"

    @staticmethod
    def resolve_stage(obj):
        if not obj.stage:
            return
        return obj.stage.name
    
    @staticmethod
    def resolve_stage_uid(obj):
        if not obj.stage:
            return
        return obj.stage.uid

    @staticmethod
    def resolve_phase(obj):
        if not obj.stage:
            return PhaseType.NEW.value
        return obj.stage.phase

    @staticmethod
    def resolve_experience(obj):
        return int(obj.applicant.years_of_experience)
    
    @staticmethod
    def resolve_match(obj):
        if hasattr(obj, "computed_match_score"):
            return 0 if not obj.computed_match_score else int(obj.computed_match_score)
        return int(obj.match) or 0

    @staticmethod
    def resolve_ai_insight(obj):
        try:
            insight = AIApplicationInsight.objects.filter(application_id=obj.id).first()
            if insight:
                return insight
            return dict()
        except:
            return dict()
        

class JobApplicationDetailSchema(JobApplicationListSchema):
    strength: Optional[JobMatchSchema] = None
    weakness: Optional[JobMatchSchema] = None
    non_negotiable: Optional[JobMatchSchema] = None
    ai_insight: AIInsightSchema
    ai_match_score: Optional[int] = 0
    top_percent: Optional[int] = 0
    rank: Optional[int] = None
    pool_size: Optional[int] = None

    @staticmethod
    def resolve_strength(obj, context):
        return obj.job_post.strength(obj.applicant)

    @staticmethod
    def resolve_weakness(obj, context):
        return obj.job_post.weakness(obj.applicant)

    @staticmethod
    def resolve_non_negotiable(obj, context):
        return obj.job_post.non_negotiable()

    @staticmethod
    def resolve_ai_insight(obj):
        try:
            insight = AIApplicationInsight.objects.filter(application_id=obj.id).first()
            if insight:
                return insight
            return dict()
        except:
            return dict()


class StageSchema(GenericNameAndUidSchema):
    phase: str


class RequirementSchema(Schema):
    requires_location: Optional[bool] = False
    missing_compulsory_secondary_language: Optional[bool] = False
    requires_role: Optional[bool] = False
    missing_required_skill: Optional[bool] = False
    requires_job_level: Optional[bool] = False
    requires_experience: Optional[bool] = False
    requires_minimum_education: Optional[bool] = False
    requires_work_structure: Optional[bool] = False
    requires_tech_requirements: Optional[bool] = False
    missing_work_schedule: Optional[bool] = False

    class Meta:
        orm_mode = True

class MatchScoreSchema(Schema):
    role_score: Optional[float] = 0
    tools_platform_score: Optional[float] = 0
    methodologies_score: Optional[float] = 0
    general_skill_score: Optional[float] = 0
    business_model_score: Optional[float] = 0
    job_level_score: Optional[float] = 0
    experience_score: Optional[float] = 0
    minimum_education_score: Optional[float] = 0
    work_structure_score: Optional[float] = 0
    tech_requirement_score: Optional[float] = 0
    first_language_score: Optional[float] = 0
    additional_language_score: Optional[float] = 0
    final_work_schedule_score: Optional[float] = 0
    location_score: Optional[float] = 0
    computed_match_score: Optional[float] = 0
    requires_location: Optional[bool] = False
    missing_compulsory_secondary_language: Optional[bool] = False
    requires_role: Optional[bool] = False
    missing_required_skill: Optional[bool] = False
    requires_job_level: Optional[bool] = False
    requires_experience: Optional[bool] = False
    requires_minimum_education: Optional[bool] = False
    requires_work_structure: Optional[bool] = False
    requires_tech_requirements: Optional[bool] = False
    missing_work_schedule: Optional[bool] = False
    missing_required_business_model: Optional[bool] = False
    tools_platform_count: Optional[int] = 0
    tools_platform_intercept_count: Optional[int] = 0
    methodologies_count: Optional[int] = 0
    methodologies_intercept_count: Optional[int] = 0

    class Meta:
        orm_mode = True

    @staticmethod
    def resolve_requirements(obj):
        return RequirementSchema.from_orm(obj)


class TalentJobPostListSchema(ModelSchema):
    job: JobListSchema2
    applied: bool
    saved: Optional[bool]
    alert: Optional[bool]
    country: Optional[GenericNameAndUidSchema] = None
    match_score: Optional[int] = 0
    application_uid: Optional[UUID]
    stage: Optional[StageSchema]
    invited: bool
    city: Optional[str] = None
    province: Optional[GenericNameAndUidSchema] = None
    match_obj: Optional[MatchScoreSchema] = None
    date_saved: Optional[datetime] = None
    date_applied: Optional[datetime] = None
    about: Optional[str] = Field(None, alias="get_about")
    tags: List[str] = Field(alias="get_tags")
    linkedin_tags: List[str]
    code: str = Field(alias="get_code")
    ai_match_score: Optional[int] = 0


    class Meta:
        model = JobPost
        fields = ("uid", "job", "country", "postal_code", "status", "date_posted", "created_at",
                  "share_compensation")

    @staticmethod
    def resolve_date_saved(self, context):
        request = context.get("request")
        if not request:
            return
        talent = request.context.get("talent")
        if not talent:
            return
        saved = talent.savedjob_set.filter(job_post=self).first()
        if not saved:
            return
        return saved.created_at

    @staticmethod
    def resolve_date_applied(self, context):
        request = context.get("request")
        if not request:
            return
        talent = request.context.get("talent")
        if not talent:
            return
        applied = talent.jobapplication_set.filter(job_post=self).first()
        if not applied:
            return
        return applied.created_at

    @staticmethod
    def resolve_alert(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return
        if not hasattr(talent, "jobalert"):
            return False
        return talent.jobalert.jobs.filter(id=obj.job_id).exists()

    @staticmethod
    def resolve_invited(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        talent = request.context.get("talent")
        if not talent:
            return
        return obj.invited(talent)


    @staticmethod
    def resolve_saved(obj, context):
        request = context.get("request")
        if not request:
            return
        talent = request.context.get("talent")
        if not talent:
            return None
        return talent.savedjob_set.filter(job_post=obj).exists()

    @staticmethod
    def resolve_applied(obj, context):
        request = context.get("request")
        if not request:
            return
        talent = request.context.get("talent")
        if not talent:
            return None
        return JobApplication.objects.filter(job_post=obj, applicant=talent).exists()

    @staticmethod
    def resolve_application_uid(obj, context):
        request = context.get("request")
        if not request:
            return
        talent = request.context.get("talent")
        if not talent:
            return None
        application = JobApplication.objects.filter(job_post=obj, applicant=talent).only("uid").first()
        return application.uid if application else None

    @staticmethod
    def resolve_stage(obj, context):
        request = context.get("request")
        if not request:
            return
        talent = request.context.get("talent")
        if not talent:
            return None
        application = JobApplication.objects.filter(job_post=obj, applicant=talent).only("stage").first()
        return application.stage if application else None

    @staticmethod
    def resolve_match_score(obj, context):
        if hasattr(obj, "computed_match_score"):
            return 0 if not obj.computed_match_score else int(obj.computed_match_score)
        return 0

    @staticmethod
    def resolve_match_obj(obj, context):
        return MatchScoreSchema.from_orm(obj)

    @staticmethod
    def resolve_ai_match_score(obj, context):
        request = context.get("request")
        talent = request.context.get("talent")
        try:
            ai_match_score = AIMatchScore.objects.filter(talent_id=talent.id).first()
            if ai_match_score:
                return int(ai_match_score.score)
            return 0
        except:
            return 0


class TalentJobPostSchema(JobPostListSchema):
    job: JobDetailSchema
    strength: Optional[JobMatchSchema] = None
    weakness: Optional[JobMatchSchema] = None
    non_negotiable: JobMatchSchema
    application_uid: Optional[UUID] = None
    match_score: Optional[int] = 0
    stage: Optional[StageSchema] = None
    screening_questions: List[TalentQuestionSchema]
    country: Optional[GenericNameAndUidSchema] = None
    strength: Optional[JobMatchSchema]
    weakness: Optional[JobMatchSchema]
    non_negotiable: JobMatchSchema
    benefits: List[str]
    address: Optional[str] = Field(None, alias="get_location")

    @staticmethod
    def get_talent(context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        return request.context.get("talent")

    @staticmethod
    def resolve_match_score(obj, context):
        if hasattr(obj, "computed_match_score"):
            return 0 if not obj.computed_match_score else int(obj.computed_match_score)
        return 0

    @staticmethod
    def resolve_application_uid(obj, context):
        talent = TalentJobPostSchema.get_talent(context)
        if not talent:
            return None
        application = JobApplication.objects.filter(job_post=obj, applicant=talent).only("uid").first()
        return application.uid if application else None

    @staticmethod
    def resolve_stage(obj, context):
        talent = TalentJobPostSchema.get_talent(context)
        if not talent:
            return None
        application = JobApplication.objects.filter(job_post=obj, applicant=talent).only("stage").first()
        return application.stage if application else None

    @staticmethod
    def resolve_strength(obj, context):
        talent = TalentJobPostSchema.get_talent(context)
        if not talent:
            return
        return obj.strength(talent)


    @staticmethod
    def resolve_weakness(obj, context):
        talent = TalentJobPostSchema.get_talent(context)
        if not talent:
            return
        return obj.weakness(talent)




class TalentJobFilterQuerySchema(Schema):
    search: Optional[str] = ""
    distinct: Optional[Literal['true', 'false']] = 'false'
    work_structure:Optional[str] = Field("", description=f"comma separated work structure enums: {', '.join(WorkStructureEnum.values())}")
    company: Optional[str] = Field("", description="comma separated company uuids")
    sort_by: Optional[str] = Field("", description=f"comma separated sort fields: {', '.join(['date-posted', '-date-posted', 'match-score', '-match-score'])}")
    location: Optional[str] = Field("", description="comma separated country uuids")
    employment_type: Optional[str] = Field("", description="comma separated employment type uuids")
    job_level: Optional[str] = Field("", description="comma separated job level uuids")
    minimum_education_level: Optional[str] = Field("", description="comma separated minimum education level uuids")
    job_role: Optional[str] = Field("", description="comma separated job role uuids")
    yoe: Optional[str] = Field("", description=f"comma separated years of experience: {', '.join(['0 years', '1-3 years', '4-7 years', '7-10 years', '11-15 years', '15-20 years', '20+ years'])}")
    remove_applied_jobs: Optional[str] = Field("", description="remove applied jobs: true or false")


    def convert_to_schema(self):
        return TalentJobFilterSchema(
            distinct=self.distinct == 'true',
            search=self.search if self.search else None,
            work_structure=self.work_structure.split(",") if self.work_structure else [],
            company=self.company.split(",") if self.company else [],
            sort_by=self.sort_by.split(",") if self.sort_by else [],
            location=self.location.split(",") if self.location else [],
            employment_type=self.employment_type.split(",") if self.employment_type else [],
            job_level=self.job_level.split(",") if self.job_level else [],
            minimum_education_level=self.minimum_education_level.split(",") if self.minimum_education_level else [],
            job_role=self.job_role.split(",") if self.job_role else [],
            yoe=self.yoe.split(",") if self.yoe else [],
            remove_applied_jobs=self.remove_applied_jobs == "true" if self.remove_applied_jobs else None
        )

class TalentJobFilterSchema(Schema):
    distinct: Optional[bool] = None
    search: Optional[str] = None
    work_structure:Optional[List[WorkStructureEnum]] = []
    company: Optional[List[UUID]] = []
    sort_by: Optional[List[Literal['date-posted', '-date-posted', 'match-score', '-match-score']]] = []
    location: Optional[List[UUID]] = []
    employment_type: Optional[List[UUID]] = []
    job_level: Optional[List[UUID]] = []
    minimum_education_level: Optional[List[UUID]] = []
    job_role: Optional[List[UUID]] = []
    yoe: Optional[List[Literal[
        '0 years', '1-3 years', '4-7 years', '7-10 years', '11-15 years', '15-20 years', '20+ years'
    ]]] = []
    remove_applied_jobs: Optional[bool] = None

    def get_queryset(self, talent=None, queryset=None, extra_sorts:List[str]=None)->QuerySet:
        """
         get job post queryset based on this filter

         Args:
             talent: talent object
             queryset: Job post queryset
             extra_sorts: extra sort fields based on model fields

        Returns:
            Job post queryset
        """
        from jobs.services import order_job_posts
        if queryset is None:
            queryset = JobPost.objects.select_related("job", "country").all()
        if self.search:
            queryset = queryset.filter(job__role__name__icontains=self.search)

        if self.location:
            queryset = queryset.filter(country__uid__in=self.location)

        if self.company:
            queryset = queryset.select_related("job__created_by__business")
            queryset = queryset.filter(job__created_by__business__uid__in=self.company)
        if self.job_role:
            queryset = queryset.filter(job__role__uid__in=self.job_role)

        if self.work_structure:
            ws = [ws.value for ws in self.work_structure]
            queryset = queryset.filter(job__work_structure__in=ws)

        if self.employment_type:
            queryset = queryset.filter(job__employment_type__uid__in=self.employment_type)

        if self.job_level:
            queryset = queryset.filter(job__job_level__uid__in=self.job_level)

        if self.minimum_education_level:
            queryset = queryset.filter(job__minimum_education_level__uid__in=self.minimum_education_level)

        if self.yoe:
            query = Q()
            for yoe in set(self.yoe):
                yoe.strip()
                if yoe == "0 years":
                    query = query | Q(Q(job__years_of_experience__isnull=True)|Q(job__years_of_experience=0))
                elif yoe == "20+ years":
                    query = query | Q(job__years_of_experience__gte=20)
                elif "-" in yoe:
                    years = map(int, yoe.replace(" years", "").split("-"))
                    query = query | Q(job__years_of_experience__range=years)
            queryset = queryset.filter(query)
        if self.remove_applied_jobs is True and talent:
            applied_jobs_id = talent.jobapplication_set.only("job_post_id").values_list("job_post_id", flat=True)
            queryset = queryset.exclude(id__in=applied_jobs_id)
        if not extra_sorts:
            extra_sorts = []
        from jobs.queries import add_job_post_annotations
        queryset = add_job_post_annotations(queryset, talent).filter(status=JobStatusType.POSTED.value, can_apply=True)
        return order_job_posts(queryset,  self.sort_by, *extra_sorts, distinct=self.distinct)


class BusinessJobFilterQuerySchema(Schema):
    search: Optional[str] = ""
    work_structure:Optional[str] = Field("", description=f"comma separated work structure enums: {', '.join(WorkStructureEnum.values())}")
    clients: Optional[str] = Field("", description="comma separated clients")
    country: Optional[str] = Field(None, description="country uuid")
    province: Optional[str] = Field(None, description="province uuid")
    city: Optional[str] = Field(None, description="city name")
    status: Optional[str] = Field(None, description=f"status enums:  {', '.join(JobStatusType.values())}")
    statuses: Optional[str] = Field("", description=f"comma separated status type  enums: {', '.join(JobStatusType.values())}")
    recruiter: Optional[str] = Field("", description="comma separated recruiter uuids")
    posted_by : Optional[str] = Field("", description="comma separated recruiter uuids")
    tags: Optional[str] = Field("", description="comma separated tag uuids")
    to_excel: Optional[bool] = False


    def convert_to_schema(self):
        return BusinessJobFilterSchema(
            search=self.search if self.search else None,
            work_structure=self.work_structure.split(",") if self.work_structure else [],
            clients=self.clients.split(",") if self.clients else [],
            country=self.country,
            status=self.status,
            province=self.province,
            city=self.city,
            statuses=self.statuses.split(",") if self.statuses else [],
            recruiter=self.recruiter.split(",") if self.recruiter else [],
            posted_by=self.posted_by.split(",") if self.posted_by else [],
            tags=self.tags.split(",") if self.tags else [],
            to_excel=self.to_excel
        )

class BusinessJobFilterSchema(Schema):
    search: Optional[str] = None
    work_structure:Optional[List[WorkStructureEnum]] = []
    statuses: Optional[List[JobStatusType]] = []
    clients: Optional[List[str]] = []
    status: Optional[JobStatusType] = None
    country: Optional[UUID] = None
    province: Optional[UUID] = None
    city: Optional[str] = None
    recruiter: Optional[List[UUID]] = []
    posted_by: Optional[List[UUID]] = []
    tags: Optional[List[UUID]] = []
    to_excel: Optional[bool] = False

    def get_queryset(self, queryset=None, extra_sorts:List[str]=None)->QuerySet:
        """
         get jobs queryset based on this filter

         Args:
             business_user: talent object
             queryset: Job post queryset
             extra_sorts: extra sort fields based on model fields

        Returns:
            Job post queryset
        """
        if queryset is None:
            queryset = Job.objects.prefetch_related("jobpost_set").annotate(jobpost_count=Count('jobpost')).filter(
                jobpost_count__gt=0)
        if self.search:
            queryset = queryset.select_related("role", "created_by__business").all()
            queryset = queryset.filter(Q(role__name__icontains=self.search)|
                                       Q(hiring_company_name__icontains=self.search) |
                                       Q(created_by__business__name__icontains=self.search)
                                       ).distinct()

        job_post_query = Q()

        if self.status:
            job_post_query &= Q(status__icontains=self.status.value)

        if self.country:
            job_post_query &= Q(country__uid=self.country)

        if self.tags:
            job_post_query &= Q(tags__uid__in=self.tags)

        if self.province:
            job_post_query &= Q(province__uid=self.province)

        if self.city:
            job_post_query &= Q(city__iexact=self.city)

        if self.clients:
            queryset = queryset.filter(hiring_company_name__in=self.clients)

        if self.work_structure:
            ws = [ws.value for ws in self.work_structure]
            queryset = queryset.filter(work_structure__in=ws)

        if self.statuses:
            statuses = [s.value for s in self.statuses]
            job_post_query &= Q(status__in=statuses)

        if self.recruiter:
            job_post_query &= Q(recruiter__uid__in=self.recruiter)


        if self.posted_by:
            job_post_query &= Q(posted_by__uid__in=self.posted_by)

        return queryset.annotate(
           has_job=Exists(JobPost.objects.filter(Q(job_id=OuterRef("id")) & job_post_query))).filter(has_job=True)

    def get_context(self, context)->dict:
        if not context:
            context = {}
        if self.country:
            context["country"] = self.country
        if self.province:
            context["province"] = self.province

        if self.status:
            context["status"] = self.status.value

        if self.city:
            context["city"] = self.city

        if self.statuses:
            statuses = [s.value for s in self.statuses]
            context["statuses"] = statuses

        if self.recruiter:
            context["recruiter"] = self.recruiter

        if self.posted_by:
            context["posted_by"] = self.posted_by

        return context

    @staticmethod
    def filter_job_posts(context, queryset):
        if context.get("business"):
            queryset = queryset.filter(job__created_by__business=context.get("business"))
        if context.get("status"):
            queryset = queryset.filter(status=context.get("status"))
        if context.get("country"):
            queryset = queryset.filter(country__uid=context.get("country"))
        if context.get("province"):
            queryset = queryset.filter(province__uid=context.get("province"))
        if context.get("city"):
            queryset = queryset.filter(city__iexact=context.get("city"))
        if context.get("statuses"):
            queryset = queryset.filter(status__in=context.get("statuses"))
        if context.get("recruiter"):
            queryset = queryset.filter(recruiter__uid__in=context.get("recruiter"))
        if context.get("posted_by"):
            queryset = queryset.filter(posted_by__uid__in=context.get("posted_by"))
        return queryset


class PublicJobPostFilterQuerySchema(Schema):
    search: Optional[str] = ""
    work_structure: Optional[str] = Field("",
                                          description=f"comma separated work structure enums: {', '.join(WorkStructureEnum.values())}")
    country: Optional[str] = Field("", description="comma separated country uuids")
    employment_type: Optional[str] = Field("", description="comma separated employment type uuids")
    region: Optional[str] = Field("", description="optional: north-america")

    def convert_to_schema(self):
        return PublicJobPostFilterSchema(
            search=self.search if self.search else None,
            work_structure=self.work_structure.split(",") if self.work_structure else [],
            country=self.country.split(",") if self.country else [],
            employment_type=self.employment_type.split(",") if self.employment_type else [],
            region=self.region if self.region else None
        )


class PublicJobPostFilterSchema(Schema):
    search: Optional[str] = None
    work_structure: Optional[List[WorkStructureEnum]] = []
    country: Optional[List[UUID]] = []
    employment_type: Optional[List[UUID]] = []
    region: Optional[str] = None

    def get_queryset(self, queryset=None, extra_sorts: List[str] = None) -> QuerySet:
        """
         get jobs queryset based on this filter

         Args:
             queryset: Job post queryset
             extra_sorts: extra sort fields based on model fields

        Returns:
            Job post queryset
        """
        if queryset is None:
            queryset = JobPost.objects.select_related('job', 'country', 'province', 'job__employment_type',
                                                      'job__role').filter(status=JobStatusType.POSTED.value)

        if self.region == "north-america":
            queryset = queryset.filter(country__name__in=["Canada", "United States"])

        if self.search:
            queryset = queryset.filter(job__role__name__icontains=self.search)

        if self.country:
            queryset = queryset.filter(country__uid__in=self.country)

        if self.work_structure:
            ws = [ws.value for ws in self.work_structure]
            queryset = queryset.filter(job__work_structure__in=ws)

        if self.employment_type:
            queryset = queryset.filter(job__employment_type__uid__in=self.employment_type)
        # queryset = queryset.annotate(
        #     row_number=Window(
        #         expression=RowNumber(),
        #         partition_by=[F("job_id")],
        #
        #     )
        # ).filter(row_number=1)
        return queryset.order_by("country")


class PublicJobPostListSchema(ModelSchema):
    role: Optional[str]
    work_structure: Optional[str] = Field(alias="job.work_structure")
    employment_type: Optional[str]
    country: Optional[str] = Field(None, alias="get_country")
    city: Optional[str] = Field(None, alias="get_city")
    province: Optional[str] = Field(None, alias="get_province")

    class Meta:
        model = JobPost
        fields = ["uid", ]

    @staticmethod
    def resolve_role(obj):
        if not obj.job.role:
            return None
        return obj.job.role.name

    @staticmethod
    def resolve_employment_type(obj):
        if not obj.job.employment_type:
            return None
        return obj.job.employment_type.fullname(public=True)


class TalentJobApplicationWithdrawalSchema(Schema):
       feedback_type: WithdrawalFeedbackType
       feedback: str

class ShareJobViaEmailSchema(Schema):
    emails: List[str]
    jobs: List[UUID]


class ShareJobViaChatSchema(Schema):
    talents: List[UUID]
    jobs: List[UUID]

class InviteToApplySchema(Schema):
    talents: List[UUID]
    jobs: List[UUID]

class MicroApplicationSchema(ModelSchema):
    stage: Optional[StageSchema]

    class Meta:
        model = JobApplication
        fields = ("uid",)

class TalentListJobPostSchema(ModelSchema):
    first_name: str = Field(alias="user.first_name")
    last_name: str = Field(alias="user.last_name")
    user_uid: UUID = Field(alias="user.uid")
    email: EmailStr = Field(alias="user.email")
    phone_number: Optional[str] = Field(None, alias="user.phone_number")
    phone_code: Optional[str] = Field(None, alias="user.phone_code")
    photo_url: Optional[str]
    cv_url: Optional[str]
    match_score: Optional[int]
    role: Optional[GenericNameAndUidSchema] = Field(None, alias="get_role")
    country: Optional[GenericNameAndUidSchema]
    years_of_experience: str = Field(alias="get_years_of_experience")
    average_experience_tenure: str = Field(alias="get_average_experience_tenure")
    ai_match_score: Optional[int] = None

    class Meta:
        model = Talent
        fields = ("uid", "job_type")

    @staticmethod
    def resolve_match_score(obj, context)->Optional[int]:
       return int(obj.computed_match_score) if obj.computed_match_score else 0


class TalentListJobPostSchema2(TalentListJobPostSchema):
    invited: bool
    application: Optional[MicroApplicationSchema]

    @staticmethod
    def resolve_invited(obj, context) -> bool:
        request = context.get("request")
        job_post = request.context.get("job_post")
        return JobInvite.objects.filter(job=job_post.job, talent=obj).exists()

    @staticmethod
    def resolve_application(obj, context):
        request = context.get("request")
        job_post = request.context.get("job_post")
        return JobApplication.objects.filter(job_post=job_post, applicant=obj).first()


class UpdateApplicationSchema(Schema):
    stages: List[UUID]

class BulkUpdateApplicationSchema(Schema):
    stages: List[UUID]
    uids: List[UUID]


class ApplyToJobSchema(Schema):
    answers:Optional[List[MutateAnswerSchema]]=None
    available_for_schedule:bool


class BulkJobPostSchema(Schema):
    job_posts: List[UUID]
    action: ActionType


class BusinessUserJobSchema(ModelSchema):
    created_by: BusinessUserListSchema
    title: Optional[str] = Field(alias="get_title")

    class Meta:
        model = Job
        fields = ["uid"]


class TalentScreeningResultSchema(ModelSchema):
    role: Optional[GenericNameAndUidSchema] = Field(None, alias="job_post.job.role")
    stage: Optional[GenericNameAndUidSchema] = None
    location: Optional[GenericNameAndUidSchema] = Field(None, alias="job_post.country")
    client: Optional[str] = Field(None, alias="job_post.job.get_company")
    result: Optional[str] = Field(None, alias="get_screening_result_status")
    date_submitted: Optional[datetime] = Field(None, alias="created_at")
    job_post_uid: Optional[UUID] = Field(None, alias="job_post.uid")

    class Meta:
        model = JobApplication
        fields = ["uid", "updated_at"]


class UpdateQuickReviewSchema(Schema):
    action: UpdateQuickReviewType
    applications: List[UUID]

class QuickReviewFilterSchema(Schema):
    job: Optional[UUID] = None
    job_posts: Optional[List[UUID]] = None

class QuickReviewFilterQuerySchema(Schema):
    job: Optional[str] = Field(None, description="job uuid")
    job_posts: Optional[str] = Field("", description="job posts uuids separated by comma")

    def convert_to_schema(self):
        return QuickReviewFilterSchema(
            job=self.job if self.job else None,
            job_posts=self.job_posts.split(",") if self.job_posts else [],
        )


class AIJobDescriptionGeneratorRequestSchema(Schema):
    prompt: Optional[str] = None


class AIJobDescriptionGeneratorResponseSchema(Schema):
    role: GenericNameAndUidSchema
    job_description: str
    responsibilities: str
    skills: List[JobSkillSchema]
    job_level: Optional[GenericNameAndUidSchema]
    additional_skills: List[str]
    years_of_experience: Optional[int] = None
    work_structure: Optional[WorkStructureEnum] = None
    country: Optional[GenericNameAndUidSchema] = None
    state: Optional[GenericNameAndUidSchema] = None
    city: Optional[GenericNameAndUidSchema] = None


class AIJobSalaryItemSchema(Schema):
    salary_type: str = Field(examples=SalaryType.values())
    salary_min: float
    salary_max: float

    @staticmethod
    def salary_item(salary_type, salary_min, salary_max):
        return {
            "salary_type": salary_type.value,
            "salary_min": round(salary_min, 1),
            "salary_max": round(salary_max, 1),
        }

class AIJobSalaryGeneratorResponseSchema(Schema):
    salary_options: List[AIJobSalaryItemSchema]
    bonus_salary_options : List[AIJobSalaryItemSchema]
    currency: GenericNameAndUidSchema

    @staticmethod
    def build_salary_options(annual_min, annual_max, hourly_min, hourly_max):
        return [
            AIJobSalaryItemSchema.salary_item(SalaryType.ANNUALLY, annual_min, annual_max),
            AIJobSalaryItemSchema.salary_item(SalaryType.HOURLY, hourly_min, hourly_max),
            AIJobSalaryItemSchema.salary_item(SalaryType.BI_MONTHLY, annual_min / 6, annual_max / 6),
            AIJobSalaryItemSchema.salary_item(SalaryType.BI_WEEKLY, annual_min / 24, annual_max / 24),
            AIJobSalaryItemSchema.salary_item(SalaryType.DAILY, hourly_min * 8, hourly_max * 8),
            AIJobSalaryItemSchema.salary_item(SalaryType.MONTHLY, annual_min / 12, annual_max / 12),
            AIJobSalaryItemSchema.salary_item(SalaryType.WEEKLY, annual_min / 48, annual_max / 48)
        ]

    @classmethod
    def example(cls):
        currency = Currency.objects.filter(abbreviation__iexact="USD").first()
        return {
                "salary_options": [
                    {
                        "salary_type": SalaryType.ANNUALLY.value,
                        "salary_min": round(90000.0, 1),
                        "salary_max": round(170000.0, 1),
                    },
                    {
                        "salary_type": SalaryType.HOURLY.value,
                        "salary_min": round(45.0, 1),
                        "salary_max": round(85.0, 1),
                    },
                    {
                        "salary_type": SalaryType.BI_MONTHLY.value,
                        "salary_min": round(90000.0 / 6, 1),
                        "salary_max": round(170000.0 / 6, 1),
                    },
                    {
                        "salary_type": SalaryType.BI_WEEKLY.value,
                        "salary_min": round(90000.0 / 24, 1),
                        "salary_max": round(170000.0 / 24, 1),
                    },
                    {
                        "salary_type": SalaryType.DAILY.value,
                        "salary_min": round(45.0 * 8, 1),
                        "salary_max": round(85.0 * 8, 1),
                    },
                    {
                        "salary_type": SalaryType.MONTHLY.value,
                        "salary_min": round(90000.0 / 12, 1),
                        "salary_max": round(170000.0 / 12, 1),
                    },
                    {
                        "salary_type": SalaryType.WEEKLY.value,
                        "salary_min": round(90000.0 / 48, 1),
                        "salary_max": round(170000.0 / 48, 1),
                    },
                ],

                "bonus_salary_options": [
                    {
                        "salary_type": SalaryType.ANNUALLY.value,
                        "salary_min": round(8000.0, 1),
                        "salary_max": round(25000.0, 1),
                    },
                    {
                        "salary_type": SalaryType.HOURLY.value,
                        "salary_min": round(5.0, 1),
                        "salary_max": round(15.0, 1),
                    },
                    {
                        "salary_type": SalaryType.BI_MONTHLY.value,
                        "salary_min": round(8000.0 / 6, 1),
                        "salary_max": round(25000.0 / 6, 1),
                    },
                    {
                        "salary_type": SalaryType.BI_WEEKLY.value,
                        "salary_min": round(8000.0 / 24, 1),
                        "salary_max": round(25000.0 / 24, 1),
                    },
                    {
                        "salary_type": SalaryType.DAILY.value,
                        "salary_min": round(5.0 * 8, 1),
                        "salary_max": round(15.0 * 8, 1),
                    },
                    {
                        "salary_type": SalaryType.MONTHLY.value,
                        "salary_min": round(8000.0 / 12, 1),
                        "salary_max": round(25000.0 / 12, 1),
                    },
                    {
                        "salary_type": SalaryType.WEEKLY.value,
                        "salary_min": round(8000.0 / 48, 1),
                        "salary_max": round(25000.0 / 48, 1),
                    },
                ],

                "currency": {
                    "uid": str(currency.uid),
                    "name": currency.name,
                }
            }


class AIJobSalaryGeneratorRequestSchema(Schema):
    role: UUID
    job_description: str
    country: UUID
    state: UUID
    job_level: UUID
    department: UUID
    employment_type: UUID


class MutateApplicationNoteSchema(Schema):
    application_note: Optional[str] = None
    interview_note: Optional[str] = None
    rejection_reason: Optional[RejectionReasonType] = None
    rejection_note: Optional[str] = None


class ApplicationNoteSchema(ModelSchema):
    application_note_by: Optional[BusinessUserListSchema] = None
    interview_note_by: Optional[BusinessUserListSchema] = None
    rejection_note_by: Optional[BusinessUserListSchema] = None
    class Meta:
        model = JobApplicationNotes
        fields = ["application_note", "interview_note", "rejection_reason", "rejection_note",
                  "application_note_at", "interview_note_at", "rejection_note_at",
                  ]



