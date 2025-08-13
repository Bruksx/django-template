from datetime import date
from typing import Optional, List, TypedDict
from uuid import UUID

from django.db.models import Q
from ninja import ModelSchema, Schema
from pydantic import EmailStr, Field

from accounts.enums import BusinessUserRoleType
from accounts.models import Business, BusinessUser, TalentFilter, Talent, Experience, Education
from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS, GenericNameAndUidSchema, EducationLevelSchema
from jobs.enums import WorkStructureEnum
from jobs.models import EmploymentType


class ValidateOTPSchema(Schema):
    email: EmailStr
    otp: str
    first_name: str
    last_name: str
    role: str
    company_name: str
    password: str
    phone_code: Optional[str] = None
    phone_number: Optional[str] = None


class CompleteBusinessProfileSchema(ModelSchema):
    industry_uid: Optional[UUID] = None
    country_uid: Optional[UUID] = None

    class Meta:
        model = Business
        fields = ["size", "description", "website", "address", "instagram", "linkedin", "facebook",
                  "twitter_x"]

class BusinessSchema(ModelSchema):
    industry: GenericNameAndUidSchema

    class Meta:
        model = Business
        fields = ["size", "description", "website", "address", "logo", "instagram", "linkedin", "facebook",
                  "twitter_x", "industry"]


class EmploymentTypeSchema(ModelSchema):
    # sub_types: list[EmploymentTypeSchema]
    class Meta:
        model = EmploymentType
        fields = ["uid", "name"]


class DashboardFilterSchema(TypedDict):
    start_date: Optional[str]
    end_date: Optional[str]
    role: Optional[UUID]
    client: Optional[str]

class Last3MonthHiresSchema(Schema):
    role: str
    talent: str
    hired_by: str

class RecruiterPerformanceListSchema(Schema):
    recruiter: str
    count: int

class RecruiterPerformanceSchema(Schema):
    total_hires: int
    data:List[RecruiterPerformanceListSchema]

class ApplicationGenderListSchema(Schema):
    gender: str
    count: int

class ApplicationGenderSchema(Schema):
    total_hires: int
    data: List[ApplicationGenderListSchema]

class HiresByCountryListSchema(Schema):
    country: str
    count: int

class HiresByCountrySchema(Schema):
    total_countries: int
    data: List[HiresByCountryListSchema]

class TimeToHireSchema(Schema):
    role: str
    posted: Optional[int] = None
    screening: Optional[int] = None
    interview: Optional[int] = None
    onboarding: Optional[int] = None
    days_to_hire: int

class StageTimelineSchema(Schema):
    stage: str
    avg_timeline: int|float

class TimeToHireViaStages(Schema):
    role: str
    graph: List[StageTimelineSchema]
    days_to_hire: int|float


class WithdrawalReasonSchemaList(Schema):
    reason: str
    count: int

class WithdrawalReasonSchema(Schema):
    total_withdrawal: int
    data: List[WithdrawalReasonSchemaList]


class ApplicantsYearsOfExperienceSchema(Schema):
    years_of_experience:str
    count:int


class TalentByPhase(Schema):
    phase: str
    count: int

class TalentByStage(Schema):
    stage: str
    count: int

class DashboardSchema(ModelSchema):
    # would need to be cached
    hires:int
    open_roles:int
    applicants:int
    avg_days_to_hire:int
    invitations_sent: int

    hires_last_3_months:List[Last3MonthHiresSchema]
    recruiter_performance:RecruiterPerformanceSchema
    applicant_gender:ApplicationGenderSchema
    hires_location:HiresByCountrySchema
    time_to_hire:List[TimeToHireSchema]
    stage_timelines: List[TimeToHireViaStages]
    withdrawal_reasons: WithdrawalReasonSchema
    applicants_years_of_experience: List[ApplicantsYearsOfExperienceSchema]
    talents_by_phase:List[TalentByPhase]
    talents_by_stage: List[TalentByStage]

    class Meta:
        model = Business
        fields = ("uid", )

    @staticmethod
    def get_context(obj, context):
        return dict(
            start_date=context.get("start_date"),
            end_date=context.get("end_date"),
            role_id=context.get("role_id"),
            client=context.get("client")
        )

    @staticmethod
    def resolve_hires(obj, context):
        return obj.total_hires(**DashboardSchema.get_context(obj, context))

    @staticmethod
    def resolve_open_roles(obj, context):
        return obj.total_open_roles(**DashboardSchema.get_context(obj, context))

    @staticmethod
    def resolve_applicants(obj, context):
        return obj.total_applicants(**DashboardSchema.get_context(obj, context))

    @staticmethod
    def resolve_avg_days_to_hire(obj, context):
        return obj.average_days_to_hire(**DashboardSchema.get_context(obj, context))

    @staticmethod
    def resolve_invitations_sent(obj, context):
        return obj.total_invitations_sent(**DashboardSchema.get_context(obj, context))
    @staticmethod
    def resolve_hires_last_3_months(obj, context):
        return [Last3MonthHiresSchema(**data)
                for data in obj.hires_last_3_months
                (role_id=context.get("role_id"),
                 client=context.get("client"))]


    @staticmethod
    def resolve_recruiter_performance(obj, context):
        data = dict(total_hires=0, data=list())
        data["total_hires"], data["data"] = obj.recruiter_performance(
           **DashboardSchema.get_context(obj, context)
        )
        return RecruiterPerformanceSchema.from_orm(data)

    @staticmethod
    def resolve_applicant_gender(obj, context):
        data = dict(total_hires=0, data=list())
        data["total_hires"], data["data"] = obj.hired_genders(
            **DashboardSchema.get_context(obj, context)
        )
        return ApplicationGenderSchema.from_orm(data)

    @staticmethod
    def resolve_hires_location(obj, context):
        data= dict(total_countries=0, data=list())
        data["total_countries"], data["data"] = obj.location_of_hires(
            **DashboardSchema.get_context(obj, context)
        )
        return HiresByCountrySchema.from_orm(data)

    @staticmethod
    def resolve_time_to_hire(obj, context):
        return [TimeToHireSchema(**data) for data in
                obj.time_to_hire(
                    **DashboardSchema.get_context(
                        obj, context
                    )
                )]
    @staticmethod
    def resolve_stage_timelines(obj, context):
        return [
            TimeToHireViaStages(**data) for data in
            obj.time_to_hire_via_stage(
                **DashboardSchema.get_context(
                    obj, context
                )
            )
        ]

    @staticmethod
    def resolve_withdrawal_reasons(obj, context):
        data = dict(total_withdrawal=0, data=list())
        data["total_withdrawal"], data["data"] = obj.withdrawal_reasons(
                **DashboardSchema.get_context(obj, context)
            )
        return WithdrawalReasonSchema.from_orm(data)

    @staticmethod
    def resolve_applicants_years_of_experience(obj, context):
        return [ApplicantsYearsOfExperienceSchema(**data) for data in obj.applicants_years_of_experience(
            **DashboardSchema.get_context(obj, context)
        )]


    @staticmethod
    def resolve_talents_by_phase(obj, context):
        return [TalentByPhase(**data) for data in obj.talent_at_each_phase(
            **DashboardSchema.get_context(obj, context)
        )]

    @staticmethod
    def resolve_talents_by_stage(obj, context):
        return [TalentByStage(**data) for data in obj.talent_at_each_stage(
            **DashboardSchema.get_context(obj, context)
        )]

class MutateBusinessSchema(ModelSchema):
    password:str
    country: UUID
    industry_uid: Optional[UUID] = None
    class Meta:
        model = Business
        fields = (
            "name", "size", "description", "website", "address", "instagram", "linkedin", "facebook", 
            "twitter_x",
        )


class BusinessDetailSchema(ModelSchema):
    logo: Optional[str] = Field(alias="get_logo")
    location: str = Field(alias="location")
    country: Optional[GenericNameAndUidSchema] = None
    industry: Optional[GenericNameAndUidSchema] = None
    class Meta:
        model = Business
        exclude = (*READ_EXCLUDE_FIELDS, "created_by")

class BusinessUserListSchema(ModelSchema):
    fullname:str = Field(alias="user.fullname")
    first_name: str = Field(alias="user.first_name")
    last_name: str = Field(alias="user.last_name")
    email: EmailStr = Field(alias="user.email")
    user_uid: UUID = Field(alias="user.uid")
    added_by: Optional[str] = Field(alias="get_added_by")
    last_active: Optional[date]
    class Meta:
        model = BusinessUser
        fields = ("role", "uid", "status", "created_at")


class AddBusinessUserSchema(Schema):
    first_name: str
    last_name: str
    email: EmailStr
    role: BusinessUserRoleType


class MutateBusinessUserSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: BusinessUserRoleType


class AcceptBusinessUserInviteSchema(Schema):
    code: str
    password: str

class SendEmailSchema(Schema):
    emails: List[str]
    subject: str
    body : str
    from_email: str

class SendBulkChatSchema(Schema):
    talent_uids: List[str] = Field(description="List of talent UIDs")
    subject: str
    body : str

class TalentFilterQuerySchema(ModelSchema):
    role: Optional[UUID] = Field(None, description="Role UID")
    industry: Optional[UUID] = Field(None, description="Industry UID")
    languages: Optional[List[UUID]] = None
    educational_level: Optional[UUID] = None
    work_structure: Optional[WorkStructureEnum] = None
    skills: Optional[List[UUID]] = None

    class Meta:
        model = TalentFilter
        fields = ["location", "maximum_notice_period"]
        optional_fields = fields

    def get_queryset(self, queryset=None):
        if not queryset:
            queryset = Talent.objects.all()
        if self.role:
            ids = Experience.objects.filter(role__uid=self.role).only("talent_id").distinct("talent_id").values_list(
                "talent_id", flat=True)
            queryset = queryset.filter(id__in=ids)
        if self.industry:
            queryset = queryset.filter(skills__department__industry__uid=self.industry)
        if self.location:
            queryset = queryset.filter(Q(country__name__icontains=self.location) |
                                       Q(state__icontains=self.location) | Q(city__icontains=self.location))
        if self.languages:
            queryset = queryset.filter(Q(native_language__uid__in=self.languages) |
                                       Q(additional_languages__uid__in=self.languages))
        if self.educational_level:
            ids = Education.objects.filter(level__uid=self.educational_level).only("talent_id").distinct(
                "talent_id").values_list("talent_id", flat=True)
            queryset = queryset.filter(id__in=ids)
        if self.work_structure:
            queryset = queryset.filter(work_models__contains=[self.work_structure.value])
        if self.skills:
            queryset = queryset.filter(skills__uid__in=self.skills)
        if self.maximum_notice_period:
            queryset = queryset.filter(notice_period__lte=self.maximum_notice_period)
        return queryset

    def to_url_params(self, start=True):
        params = ""
        get_sign =  lambda : "&" if "?" in params else "?" if start is True else "&"
        if self.role :
            params += f"{get_sign()}role={self.role}"
        if self.industry:
            params += f"{get_sign()}industry={self.industry}"
        if self.languages:
            params += f"{get_sign()}languages={','.join(map(str,self.languages))}"
        if self.educational_level:
            params += f"{get_sign()}educational_level={self.educational_level}"
        if self.work_structure:
            params += f"{get_sign()}work_structure={self.work_structure.value}"
        if self.skills:
            params += f"{get_sign()}skills={','.join(map(str, self.skills))}"
        if self.maximum_notice_period:
           params += f"{get_sign()}maximum_notice_period={self.maximum_notice_period}"
        return params

class MutateTalentFilterSchema(ModelSchema):
    role: Optional[UUID] = Field(None, description="Role UID")
    industry: Optional[UUID] = Field(None, description="Industry UID")
    languages: Optional[List[UUID]] = None
    educational_level: Optional[UUID] = None
    work_structure: Optional[WorkStructureEnum] = None
    skills: Optional[List[UUID]] = None

    class Meta:
        model = TalentFilter
        fields = ["name", "location", "maximum_notice_period"]
        optional_fields = fields



class TalentFilterSchema(ModelSchema):
    role: Optional[GenericNameAndUidSchema]
    industry: Optional[GenericNameAndUidSchema]
    languages: Optional[List[GenericNameAndUidSchema]]
    educational_level: Optional[EducationLevelSchema]
    skills: Optional[List[GenericNameAndUidSchema]]

    class Meta:
        model = TalentFilter
        fields = ["uid","name", "location", "maximum_notice_period", "work_structure"]
        optional_fields = fields

class TalentFilterListSchema(ModelSchema):
    class Meta:
        model = TalentFilter
        fields = ["uid", "name", ]

class TransferRoleSchema(Schema):
    from_business_user: UUID
    to_business_user: UUID


class ReassignJobPostInputSchema(Schema):
    nominee_uid: UUID