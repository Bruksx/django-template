from typing import Optional, List, TypedDict
from uuid import UUID

from ninja import ModelSchema, Schema
from pydantic import EmailStr, Field

from accounts.models import Business
from jobs.models import EmploymentType
from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS



class ValidateOTPSchema(Schema):
    email: EmailStr
    otp: str
    first_name: str
    last_name: str
    role: str
    company_name: str
    password: str


class BusinessSchema(ModelSchema):
    class Meta:
        model = Business
        fields = ["size", "description", "website", "industry", "address", "country", "logo", "instagram", "linkedin", "facebook",
                  "twitter_x"]


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
    posted: int
    screening: int
    first_interview: int
    second_interview: int
    onboarding: int
    days_to_hire: int

class WithdrawalReasonSchemaList(Schema):
    reason: str
    count: int

class WithdrawalReasonSchema(Schema):
    total_withdrawal: int
    data: List[WithdrawalReasonSchemaList]


class ApplicantsYearsOfExperienceSchema(Schema):
    years_of_experience:str
    count:int


class TalentPerStage(Schema):
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
    withdrawal_reasons: WithdrawalReasonSchema
    applicants_years_of_experience: List[ApplicantsYearsOfExperienceSchema]
    talent_per_stage:List[TalentPerStage]

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
    def resolve_talent_per_stage(obj, context):
        return [TalentPerStage(**data) for data in obj.talent_at_each_stage(
            **DashboardSchema.get_context(obj, context)
        )]

class MutateBusinessSchema(ModelSchema):
    password:str
    country: UUID
    class Meta:
        model = Business
        exclude = (*MUTATE_EXCLUDE_FIELDS, "logo", "created_by", "uid")


class BusinessDetailSchema(ModelSchema):
    logo: Optional[str] = Field(alias="get_logo")
    location: str = Field(alias="location")
    class Meta:
        model = Business
        exclude = (*READ_EXCLUDE_FIELDS,)


