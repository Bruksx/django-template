from datetime import date
from typing import Optional, List, TypedDict, Any
from uuid import UUID

from accounts.enums import BusinessUserRoleType
from accounts.models import Business, BusinessUser, TalentFilter, Talent, Experience, Education
from accounts.queries import add_profile_completion_annotation
from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS, GenericNameAndUidSchema, EducationLevelSchema
from django.db.models import Q, Subquery
from django.db.models.functions import Lower
from jobs.enums import WorkStructureEnum
from jobs.models import EmploymentType
from ninja import ModelSchema, Schema
from pydantic import EmailStr, Field


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
    name: str = Field(alias="fullname")
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
    total_applicants: int
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
    days_to_hire: Any

class StageTimelineSchema(Schema):
    stage: str
    avg_timeline: Any

class TimeToHireViaStages(Schema):
    role: str
    graph: List[StageTimelineSchema]
    days_to_hire: Any


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
    applications:int
    avg_days_to_hire:int
    invitations_sent: int

    hires_last_3_months:List[Last3MonthHiresSchema]
    recruiter_performance:RecruiterPerformanceSchema
    applicant_gender:ApplicationGenderSchema
    hires_location:HiresByCountrySchema
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
    def resolve_applications(obj, context):
        return obj.total_applications(**DashboardSchema.get_context(obj, context))

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
        data = dict(total_applicants=0, data=list())
        try:
            data["total_applicants"], data["data"] = obj.applicants_by_gender(
                **DashboardSchema.get_context(obj, context)
            )
            print(data)
        except Exception as e:
            print(e)
        finally:
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
    roles: Optional[List[UUID]] = None
    industries: Optional[List[UUID]] = None
    languages: Optional[List[UUID]] = None
    educational_levels: Optional[List[UUID]] = None
    work_structure: Optional[WorkStructureEnum] = None
    skills: Optional[List[UUID]] = None
    locations: Optional[List[str]] = None
    business_models: Optional[List[UUID]] = None
    completed_profiles: Optional[bool] = None
    

    class Meta:
        model = TalentFilter
        fields = ["maximum_notice_period"]
        optional_fields = fields

    def get_queryset(self, queryset=None):
        queryset = queryset or Talent.objects.all()


        # Filter by roles via Experience (subquery = optimal)
        if self.roles:
            queryset = queryset.filter(
                id__in=Subquery(
                    Experience.objects.filter(
                        role__uid__in=self.roles
                    ).values("talent_id").distinct()
                )
            )
        
        # Industries
        if self.industries:
            queryset = queryset.filter(
                skills__department__industry__uid__in=self.industries
            )

        if self.completed_profiles is not None:
            queryset = add_profile_completion_annotation(queryset)
            queryset = queryset.filter(
                complete_profile=self.completed_profiles
            )
        
        # Locations (vectorized, no loop)
        if self.locations:
            self.locations = list(map(lambda x: str(x).lower(), self.locations))
            queryset = queryset.annotate(
                country_name=Lower("country__name")
            ).filter(country_name__in=self.locations)
        
        # Languages
        if self.languages:
            queryset = queryset.filter(
                Q(native_language__uid__in=self.languages) |
                Q(additional_languages__uid__in=self.languages)
            )
        
        # Education levels
        if self.educational_levels:
            queryset = queryset.filter(
                id__in=Subquery(
                    Education.objects.filter(
                        level__uid__in=self.educational_levels
                    ).values("talent_id").distinct()
                )
            )
        
        # Work preference
        if self.work_structure:
            queryset = queryset.filter(
                work_models__contains=[self.work_structure.value]
            )
        
        # Skills
        if self.skills:
            queryset = queryset.filter(skills__uid__in=self.skills)

        # Business Model
        if self.business_models:
            queryset = queryset.filter(business_models__uid__in=self.business_models)
        
        # Notice period
        if self.maximum_notice_period:
            queryset = queryset.filter(notice_period__lte=self.maximum_notice_period)
        
        return queryset.distinct()

    def to_url_params(self, start=True):
        params = ""
        get_sign =  lambda : "&" if "?" in params else "?" if start is True else "&"
        if self.roles :
            params += f"{get_sign()}roles={','.join(map(str, self.roles))}"
        if self.industries:
            params += f"{get_sign()}industries={','.join(map(str, self.industries))}"
        if self.languages:
            params += f"{get_sign()}languages={','.join(map(str,self.languages))}"
        if self.educational_levels:
            params += f"{get_sign()}educational_levels={','.join(map(str, self.educational_levels))}"
        if self.locations:
            params += f"{get_sign()}locations={','.join(map(str, self.locations))}"
        if self.work_structure:
            params += f"{get_sign()}work_structure={self.work_structure.value}"
        if self.skills:
            params += f"{get_sign()}skills={','.join(map(str, self.skills))}"
        if self.business_models:
            params += f"{get_sign()}business_models={','.join(map(str, self.business_models))}"
        if self.maximum_notice_period:
           params += f"{get_sign()}maximum_notice_period={self.maximum_notice_period}"
        return params

class MutateTalentFilterSchema(ModelSchema):
    roles: Optional[List[UUID]] = None
    industries: Optional[List[UUID]] = None
    languages: Optional[List[UUID]] = None
    educational_levels: Optional[List[UUID]] = None
    work_structure: Optional[WorkStructureEnum] = None
    skills: Optional[List[UUID]] = None
    locations: Optional[List[str]] = None
    business_models: Optional[List[UUID]] = None

    class Meta:
        model = TalentFilter
        fields = ["name", "maximum_notice_period"]
        optional_fields = fields



class TalentFilterSchema(ModelSchema):
    roles: Optional[List[GenericNameAndUidSchema]]
    industries: Optional[List[GenericNameAndUidSchema]]
    languages: Optional[List[GenericNameAndUidSchema]]
    educational_levels: Optional[List[EducationLevelSchema]]
    skills: Optional[List[GenericNameAndUidSchema]]
    business_models: Optional[List[GenericNameAndUidSchema]]
    locations: Optional[List[str]]

    class Meta:
        model = TalentFilter
        fields = ["uid","name", "maximum_notice_period", "work_structure"]
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