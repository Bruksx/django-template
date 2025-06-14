from datetime import datetime
from typing import Optional, List
from uuid import UUID

from apps.accounts.enums import MeetingType
from ninja import Schema, ModelSchema, PatchDict
from pydantic import Field, EmailStr

from accounts.enums import GenderType, PreferredCommunicationType, Days, Months, NoticePeriodType
from accounts.models import (Talent, User, TalentAvailableDay, Education,
                             Experience, Skill, Role)
from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS, CurrencySchema, LanguageSchema, \
    EducationLevelSchema, CountrySchema
from jobs.enums import WorkStructureEnum
from jobs.schemas import JobLevelSchema, EmploymentTypeSchema, BusinessModelSchema


class DepartmentSchema(Schema):
    uid: UUID
    name: str

class RoleSchema(ModelSchema):
    department: str
    class Meta:
        model = Role
        fields = ("uid", "name", "department")

    @staticmethod
    def resolve_department(obj):
        return obj.department.name


class EducationSchema(ModelSchema):
    level: EducationLevelSchema

    class Meta:
        model = Education
        exclude = [*READ_EXCLUDE_FIELDS, "talent"]


class MutateEducationSchema(ModelSchema):
    uid: Optional[UUID] = None
    level: UUID
    class Meta:
        model = Education
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent"]


class MutateExperienceSchema(ModelSchema):
    role: UUID
    uid: Optional[UUID] = None
    annual_salary_bonus_currency: UUID
    annual_salary_currency: UUID
    employment_type: UUID
    level: Optional[UUID]
    class Meta:
        model = Experience
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent"]

class ExperienceSchema(ModelSchema):
    role: Optional[RoleSchema]
    level: Optional[JobLevelSchema]
    employment_type: EmploymentTypeSchema
    annual_salary_currency: Optional[CurrencySchema]
    annual_salary_bonus_currency: Optional[CurrencySchema]
    duration: str
    class Meta:
        model = Experience
        exclude = [*READ_EXCLUDE_FIELDS, "talent"]


class SkillSchema(ModelSchema):
    department: DepartmentSchema
    class Meta:
        model = Skill
        fields = ("uid",  "name")



class MutateTalentAvailableDaySchema(ModelSchema):
    uid: Optional[UUID] = None
    active: Optional[bool] = True
    day: Days
    class Meta:
        model = TalentAvailableDay
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent"]

class TalentAvailableDaySchema(ModelSchema):
    class Meta:
        model = TalentAvailableDay
        fields = ("uid", "start_time", "end_time")

class UpdateTalentProfileSchema(Schema):
    first_name: Optional[str]
    last_name: Optional[str]

class UpdateTalentProfileSchema2(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_communication: Optional[PreferredCommunicationType|str] = None
    phone_number: Optional[str] = None
    country: Optional[UUID] = None
    state: Optional[str] = None
    city: Optional[str] = None
    role: Optional[UUID] = None
    employment_type: Optional[UUID] = None
    postal_code: Optional[str] = None
    whatsapp_number: Optional[str] = None
    work_model: Optional[WorkStructureEnum|str] = None
    viber_number: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[GenderType] = None
    visible: Optional[bool] = None
    bio: Optional[str] = None
    notice_period: Optional[int|str] = None
    notice_period_type: Optional[NoticePeriodType|str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    facebook: Optional[str] = None
    twitter_x: Optional[str] = None
    native_language: Optional[UUID] = None
    additional_languages: Optional[List[UUID]] = None
    education_history: Optional[List[PatchDict[MutateEducationSchema]]] = None
    experience_history: Optional[List[PatchDict[MutateExperienceSchema]]] = None
    availability : Optional[List[PatchDict[MutateTalentAvailableDaySchema]]] = None
    skills: Optional[List[UUID]] = None
    additional_skills: Optional[List[str]] = None
    business_models: Optional[List[UUID]] = None




class ValidateTalentOTPSchema(UpdateTalentProfileSchema):
    otp: str
    password: str
    email: EmailStr


class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ["uid", "email", "first_name", "last_name", "phone_number",
                  "gender"]

class LoggedInUserSchema(UserSchema):
    token: str

class TalentSkillSchema(Schema):
    category :str
    skills : List[SkillSchema]

class TalentAvailabilitySchema(Schema):
    day: str
    availability: Optional[TalentAvailableDaySchema] = None

class TalentUserSchema(ModelSchema):
    user: UserSchema
    role: Optional[RoleSchema]
    country: Optional[CountrySchema]
    employment_type: Optional[EmploymentTypeSchema]
    skills: List[TalentSkillSchema]
    business_models: List[BusinessModelSchema]
    experience_history: List[ExperienceSchema]
    education_history: List[EducationSchema]
    photo_url: Optional[str]
    cv_url: Optional[str]
    native_language: Optional[LanguageSchema]
    additional_languages: List[LanguageSchema]
    availability:  List[TalentAvailabilitySchema]
    additional_skills: List[str]
    years_of_experience: str = Field(alias="get_years_of_experience")

    class Meta:
        model = Talent
        exclude = (*READ_EXCLUDE_FIELDS, "cv", "photo", "months_of_experience")

    @staticmethod
    def resolve_skills(obj):
        return obj.get_skills()

    @staticmethod
    def resolve_availability(obj):
        return obj.get_available_days()

class TalentResumeSchema(ModelSchema):
    photo_url: Optional[str]
    name: str = Field(alias="user.fullname")
    email: EmailStr = Field(alias="user.email")
    phone_number: str = Field(alias="user.phone_number")
    bio: str
    address: str
    languages: str
    skills: List[TalentSkillSchema]
    availability: List[TalentAvailabilitySchema]
    notice_period: Optional[str] = None
    experience_history: List[ExperienceSchema]
    education_history: List[EducationSchema]

    class Meta:
        model = Talent
        fields = ("bio", )

    @staticmethod
    def resolve_address(obj):
        address_list = []
        if obj.address:
            address_list.append(obj.address)
        if obj.city:
            address_list.append(obj.city)
        if obj.state:
            address_list.append(obj.state)
        if obj.country:
            address_list.append(obj.country.name)
        return ", ".join(address_list)

    @staticmethod
    def resolve_notice_period(obj):
        if not obj.notice_period or not obj.notice_period_type:
            return
        return f"{obj.notice_period} {obj.notice_period_type}"

    @staticmethod
    def resolve_languages(obj):
        languages = set()
        if obj.native_language:
            languages.add(obj.native_language.name)
        if obj.additional_languages:
            languages.update(set(obj.additional_languages.values_list("name", flat=True)))
        return ", ".join(languages)

    @staticmethod
    def resolve_skills(obj):
        return obj.get_skills()

    @staticmethod
    def resolve_availability(obj):
        return obj.get_available_days()



class TalentUserListSchema(ModelSchema):
    first_name: str =  Field(alias="user.first_name")
    last_name: str = Field(alias="user.last_name")
    email: EmailStr = Field(alias="user.email")
    user_uid: UUID = Field(alias="user.uid")
    role: Optional[RoleSchema]
    country: Optional[CountrySchema]
    phone_number: Optional[str] = Field(alias="user.phone_number")
    photo_url:Optional[str]
    cv_url:Optional[str]
    class Meta:
        model = Talent
        fields = ("uid", "years_of_experience",  )


class CompleteTalentProfileSchema(ModelSchema):
    gender: GenderType
    availability: List[MutateTalentAvailableDaySchema]
    photo: Optional[str] = None
    notice_period_type: NoticePeriodType

    class Meta:
        model = Talent
        fields = ["bio", "visible", "photo", "notice_period", "notice_period_type",
                 "instagram", "linkedin", "facebook", "twitter_x"]



class CompleteTalentProfileSchema2(ModelSchema):
    education_history: List[MutateEducationSchema]
    native_language: Optional[UUID] = None
    additional_languages:List[UUID]


    class Meta:
        model = Talent
        fields = ["additional_languages", "native_language"]


class CompleteTalentProfileSchema3(ModelSchema):

    experience_history: List[MutateExperienceSchema]

    class Meta:
        model = Talent
        fields = ["skills", "business_models"]


class TalentDashboardReport(Schema):
    job_matches: int
    jobs_applied: int
    invitations_to_apply: int
    interviews: int
    profile_views: int

    # class Meta:
    #     model = Talent
    #     fields = ("uid",)

    @staticmethod
    def resolve_job_matches(obj, context):
        if not context:
            context = dict()
        return obj.job_post_matches(by_talent_country=False, **context).count()

    @staticmethod
    def resolve_jobs_applied(obj, context):
        if not context:
            context = dict()
        return obj.job_applications(**context).count()

    @staticmethod
    def resolve_interviews(obj, context):
        if not context:
            context = dict()
        return obj.job_interviews(**context).count()

    @staticmethod
    def resolve_invitations_to_apply(obj, context):
        if not context:
            context = dict()
        return obj.invitations_to_apply(**context)

    @staticmethod
    def resolve_profile_views(obj):
        return obj.viewers.count()


class MonthlyChartSchema(Schema):
    month: Months
    count: int

class TalentDashboardChartsSchema(Schema):
    applications: List[MonthlyChartSchema]
    interviews: List[MonthlyChartSchema]

class TalentChangePasswordSchema(Schema):
    old_password: str
    new_password: str

class ParticipantSchema(Schema):
    """Schema for meeting participants."""
    email: EmailStr = Field(description="Participant's email address")
    name: Optional[str] = Field(None, description="Participant's full name")

class MeetingSettingsSchema(Schema):
    """Schema for advanced meeting settings."""
    host_video: Optional[bool] = Field(True, description="Enable host video")
    participant_video: Optional[bool] = Field(True, description="Enable participant video")
    join_before_host: Optional[bool] = Field(False, description="Allow participants to join before host")
    mute_upon_entry: Optional[bool] = Field(True, description="Mute participants upon entry")
    approval_type: Optional[int] = Field(0, description="Approval type for participants (0 for automatic approval)")
    registration_type: Optional[int] = Field(None, description="Type of registration required (e.g., 1, 2, or 3)")

class ServiceSpecificDataSchema(Schema):
    """Schema for service-specific meeting data."""
    zoom_specific: Optional[dict] = Field(None, description="Zoom-specific data")
    teams_specific: Optional[dict] = Field(None, description="Microsoft Teams-specific data")
    google_meet_specific: Optional[dict] = Field(None, description="Google Meet-specific data")

class MeetingSchema(Schema):
    """Unified schema for scheduling meetings across services."""
    topic: str = Field(description="Meeting topic or title")
    agenda: Optional[str] = Field(None, description="Meeting agenda or description")
    start_time: datetime  = Field(description="Start time of the meeting in ISO 8601 format")
    end_time: Optional[datetime] = Field(None, description="End time of the meeting in ISO 8601 format")
    duration: Optional[int] = Field(None, description="Duration of the meeting in minutes (alternative to end_time)")
    timezone: Optional[str] = Field("UTC", description="Timezone of the meeting (e.g., 'UTC')")
    participants: Optional[List[ParticipantSchema]] = Field(
        None, description="List of participants to invite"
    )
    settings: Optional[MeetingSettingsSchema] = Field(
        None, description="Advanced meeting settings"
    )
    service_specific_data: Optional[ServiceSpecificDataSchema] = Field(
        None, description="Additional data specific to the meeting service"
    )

class ScheduleMeetingSchema(Schema):
    meeting: MeetingSchema
    meeting_type: MeetingType

class MeetingResponse(Schema):
    link: str
    url: str