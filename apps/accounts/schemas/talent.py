from typing import Optional, List
from uuid import UUID

from ninja import Schema, ModelSchema

from accounts.enums import GenderType, PreferredCommunicationType, Days
from accounts.models import (Talent, User, TalentAvailableDay, Education,
                             Experience, Skill, EducationLevel, Country, Role)
from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS, CurrencySchema, LanguageSchema
from jobs.schemas import JobLevelSchema, EmploymentTypeSchema, BusinessModelSchema


class CountrySchema(ModelSchema):
    class Meta:
        model = Country
        fields = ("uid", "name", "code")

class RoleSchema(ModelSchema):
    department: str
    class Meta:
        model = Role
        fields = ("uid", "name", "department")
    @staticmethod
    def resolve_department(obj):
        return obj.department.name


class EducationLevelSchema(ModelSchema):
    industry: str
    class Meta:
        model = EducationLevel
        fields = ("uid", "industry", "level")

    @staticmethod
    def resolve_industry(obj):
        return obj.industry.name

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
    level: UUID
    class Meta:
        model = Experience
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent"]

class ExperienceSchema(ModelSchema):
    role: RoleSchema
    level: JobLevelSchema
    employment_type: EmploymentTypeSchema
    annual_salary_currency: CurrencySchema
    annual_salary_bonus_currency: CurrencySchema
    class Meta:
        model = Experience
        exclude = [*READ_EXCLUDE_FIELDS, "talent"]


class SkillSchema(ModelSchema):
    department: str
    class Meta:
        model = Skill
        fields = ("uid", "department", "name")

    @staticmethod
    def resolve_department(obj):
        return obj.department.name


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
    first_name: str
    last_name: str
    preferred_communication: PreferredCommunicationType
    phone_number: str
    country: UUID
    state: str
    city: str
    postal_code: str


class ValidateTalentOTPSchema(UpdateTalentProfileSchema):
    otp: str
    password: str
    email: str


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
    country: Optional[CountrySchema]
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

    class Meta:
        model = Talent
        exclude = (*READ_EXCLUDE_FIELDS, "cv", "photo")

    @staticmethod
    def resolve_skills(self):
        return self.get_skills()

    @staticmethod
    def resolve_additional_skills(self):
        return self.get_addiional_skills()




class CompleteTalentProfileSchema(ModelSchema):
    gender: GenderType
    availability: List[MutateTalentAvailableDaySchema]
    photo: Optional[str] = None

    class Meta:
        model = Talent
        fields = ["bio", "visible", "photo", "notice_period", "notice_period_type",
                 "instagram", "linkedin", "facebook", "twitter_x"]



class CompleteTalentProfileSchema2(ModelSchema):
    education_history: List[MutateEducationSchema]
    cv: Optional[str] = None
    native_language: Optional[UUID]
    additional_languages:List[str]


    class Meta:
        model = Talent
        fields = ["cv", "additional_languages", "native_language"]


class CompleteTalentProfileSchema3(ModelSchema):
    skills: List[UUID]
    additional_skills: List[str]
    business_models: List[UUID]
    experience_history: Optional[List[MutateExperienceSchema]]

    class Meta:
        model = Talent
        fields = ["skills", "business_models"]


