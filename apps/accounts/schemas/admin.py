from datetime import date
from typing import Optional, List, Literal, Generic, T
from uuid import UUID

from accounts.enums import BusinessUserRoleType, BusinessUserStatusType
from accounts.enums import BusinessUserRoleType, BusinessUserStatusType, UserType, AdminRoleType
from accounts.models import BusinessUser, Business, Talent
from accounts.models import BusinessUser, Business, Talent, AdminUser
from accounts.schemas.common import DashboardFilter
from accounts.schemas.talent import TalentUserSchema, UpdateTalentProfileSchema2
from core.schemas import GenericNameAndUidSchema
from core.schemas import READ_EXCLUDE_FIELDS
from jobs.enums import PhaseType, JobStatusType
from jobs.models import JobApplication
from ninja import Schema, ModelSchema
from paginations import CustomPaginatedResponseSchema
from pydantic import EmailStr, HttpUrl, Field


class AdminDashboardFilter(DashboardFilter):
    company: Optional[UUID] = None

class BusinessUsersFilter(Schema):
    active: Optional[bool] = None
    search: Optional[str] = None


class TalentUsersFilter(Schema):
    active: Optional[bool] = None
    search: Optional[str] = None


class BusinessFilter(DashboardFilter):
    paused: Optional[bool] = None
    search: Optional[str] = None



class JobPhaseSchema(Schema):
    phase: str
    count: int
    percentage_diff: float

class BusinessMetricSchema(Schema):
    total_open_jobs: int
    total_applications: int
    total_job_shares: int
    total_job_views: int
    total_interview_invitations: int
    active_clients: int
    active_users_daily_average: int
    active_users_last_7_days: int
    job_phases: List[JobPhaseSchema]

class AverageMetricSchema(Schema):
    month: date
    average_load_time: float

class ProfileCompletionThisWeekSchema(Schema):
    complete: int
    semi_complete: int
    incomplete: int

class WithdrawalReasonSchema(Schema):
    reason: str
    count: int

class TalentMetricSchema(Schema):
    total_talent_signups: int
    total_applications: int
    active_talents: int
    profile_completion_this_week: ProfileCompletionThisWeekSchema
    withdrawal_reasons: list[WithdrawalReasonSchema]
    total_withdrawals: int

class ProfileCompletionSchema(Schema):
    month: str
    complete: int
    semi_complete: int
    incomplete: int



class TalentSignupsSchema(Schema):
    month: date
    signups: int

class TalentProfileCompletionSchema(Schema):
    month: date
    complete: int
    semi_complete: int
    incomplete: int

class MutateBusinessUserSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: BusinessUserRoleType


class CreateBusinessSchema(ModelSchema):
    country: Optional[UUID] = None
    industry: Optional[UUID] = None

    class Meta:
        model = Business
        exclude = ["uid", "created_at", "updated_at", "deleted_at", "created_by", "restored_at", "transaction_id", "id"]



class MutateBusinessSchema(ModelSchema):
    country: Optional[UUID] = None
    industry: Optional[UUID] = None
    name: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    instagram: Optional[HttpUrl] = None
    linkedin: Optional[HttpUrl] = None
    facebook: Optional[HttpUrl] = None
    twitter_x: Optional[HttpUrl] = None
    website: Optional[HttpUrl] = None
    address: Optional[str] = None

    class Meta:
        model = Business
        exclude = ["uid", "created_at", "updated_at", "deleted_at", "created_by", "restored_at", "transaction_id", "id"]


class BusinessUserListSchema(ModelSchema):
    full_name: str = Field(alias="user.fullname")
    email: EmailStr = Field(alias="user.email")
    user_access: BusinessUserRoleType = Field(alias="role")
    status: BusinessUserStatusType
    last_activity: Optional[date] = Field(alias="last_active")
    joined_date: date = Field(alias="date_joined")

    class Meta:
        model = BusinessUser
        exclude = ["created_at", "updated_at", "deleted_at", "business", "added_by"]

class BusinessListSchema(ModelSchema):
    industry: Optional[GenericNameAndUidSchema] = None
    head_office: str = Field(alias="location")
    registration_date: date = Field(alias="reg_date")

    class Meta:
        model = Business
        fields = ["uid", "name", "website", "size", "paused"]


class BusinessActionSchema(Schema):
    action: Literal["move", "pause", "archive"]

class TalentListSchema(ModelSchema):
    full_name: str = Field(alias="user.fullname")
    current_role: Optional[GenericNameAndUidSchema] = Field(None, alias="role")
    location:str = Field(alias="get_address")
    email: EmailStr = Field(alias="user.email")
    applications: int
    signup_date: date

    class Meta:
        model = Talent
        fields = ["uid"]



    @staticmethod
    def resolve_applications(obj):
        return obj.jobapplication_set.count()

    @staticmethod
    def resolve_signup_date(obj):
        return obj.created_at.date()


class BusinessUserDetailSchema(BusinessUserListSchema):
    profile_picture: Optional[str] = Field(alias="user.photo_url")

class BusinessDetailSchema(ModelSchema):
    industry: Optional[GenericNameAndUidSchema] = None
    head_office: str = Field(alias="location")
    registration_date: date = Field(alias="reg_date")
    owner_name: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    logo: Optional[str] = Field(alias="get_logo")

    class Meta:
        model = Business
        exclude = (*READ_EXCLUDE_FIELDS, "created_by")

    @staticmethod
    def resolve_owner_email(obj):
        return obj.created_by.email if obj.created_by else None

    @staticmethod
    def resolve_owner_name(obj):
        return obj.created_by.fullname if obj.created_by else None

class TalentDetailSchema(TalentUserSchema):
    ...


class MutateTalentDetailSchema(UpdateTalentProfileSchema2):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class ApplicationListSchema(ModelSchema):
    job: Optional[str]
    company: Optional[str]
    job_status: JobStatusType
    date_applied: date
    withdrawals: bool
    application_status: PhaseType

    class Meta:
        model = JobApplication
        fields = ["uid"]


class PaginatedApplicationListSchema(CustomPaginatedResponseSchema[ApplicationListSchema]):
    applications: int
    rejected: int
    withdrawals: int
    job_shares: int
    job_views: int




class BusinessJobListSchema(Schema):
    name: str
    status: JobStatusType
    application_count: int
    withdrawal_count: int
    shares: int
    views: int
    assignments: int



class PaginatedBusinessJobListSchema(CustomPaginatedResponseSchema[BusinessJobListSchema]):
   jobs_created: int
   open_jobs: int
   applications: int
   shares: int
   views: int
   withdrawal_reasons: List[WithdrawalReasonSchema]

class PaginatedMetricFilter(Schema):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: Optional[int] = None
    page_size: Optional[int] = None

class AvgLoadTimeSchema(Schema):
    average_load_time: float
    month: date

class PaginatedMetricSchema(Schema, Generic[T]):
    count: int
    number_of_pages: int
    next_page: int | None
    previous_page: int | None
    results: list[T]


class PauseResumeSchema(Schema):
    action: Literal["pause", "resume"]

class AccountStatusSchema(Schema):
    is_active: bool

class BannedUserSchema(Schema):
    uid: UUID
    email: EmailStr
    account_type:UserType


class AdminUserListSchema(ModelSchema):
    fullname: str = Field(alias="user.fullname")
    email: EmailStr = Field(alias="user.email")
    joined_date: date
    status: Literal['Active', 'Blocked']

    class Meta:
        model = AdminUser
        fields = ["uid", "role", "last_activity"]

    @staticmethod
    def resolve_status(obj):
        return "Active" if obj.user.is_active is True else "Blocked"

    @staticmethod
    def resolve_joined_date(obj):
        return obj.created_at.date()

class AdminActionSchema(Schema):
    action: Literal["block", "unblock"]
    uids: list[UUID]


class InviteAdminSchema(Schema):
    email: EmailStr
    fullname: str

class EditAdminSchema(Schema):
    email: EmailStr
    fullname: str
    role: Optional[AdminRoleType] = None



class AcceptAdminInviteSchema(Schema):
    code: str
    password: str



