from locale import currency
from typing import Optional, List, Any
from uuid import UUID

from ninja import Schema, ModelSchema
from ninja.types import DictStrAny

from accounts.enums import GenderType, PreferredCommunicationType
from accounts.models import (Talent, User, TalentAvailability, Education,
                             Experience, TalentSkill, Skill, EducationLevel, Country, SkillCategory, Department,
                             Industry)
from core.models import Language
from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS, CurrencySchema, LanguageSchema
from jobs.schemas import JobLevelSchema, EmploymentTypeSchema

class CountrySchema(ModelSchema):
    class Meta:
        model = Country
        fields = ("uid", "name", "code")


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
    uid: Optional[UUID] = None
    annual_salary_bonus_currency: UUID
    annual_salary_currency: UUID
    employment_type: UUID
    level: UUID
    class Meta:
        model = Experience
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent"]

class ExperienceSchema(ModelSchema):
    level: JobLevelSchema
    employment_type: EmploymentTypeSchema
    annual_salary_currency: CurrencySchema
    annual_salary_bonus_currency: CurrencySchema
    class Meta:
        model = Experience
        exclude = [*READ_EXCLUDE_FIELDS, "talent"]



class MutateTalentSkill(ModelSchema):
    additional_skills:List[str]
    tools: List[UUID]
    frameworks: List[UUID]
    business_models: List[UUID]
    general_skills: List[UUID]
    soft_skills: List[UUID]

    class Meta:
        model = TalentSkill
        exclude = [*MUTATE_EXCLUDE_FIELDS,"talent", "uid"]


class SkillSchema(ModelSchema):
    category: str
    department: str
    class Meta:
        model = Skill
        fields = ("uid", "category", "department", "name")

    @staticmethod
    def resolve_category(obj):
        return obj.category.name

    @staticmethod
    def resolve_department(obj):
        return obj.department.name



class TalentSkillSchema(ModelSchema):
    tools: List[SkillSchema]
    frameworks: List[SkillSchema]
    business_models: List[SkillSchema]
    general_skills: List[SkillSchema]
    soft_skills: List[SkillSchema]
    class Meta:
        model = TalentSkill
        exclude = [*READ_EXCLUDE_FIELDS,"talent"]

class MutateTalentAvailabilitySchema(ModelSchema):
    class Meta:
        model = TalentAvailability
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent", "uid"]

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


class TalentUserSchema(ModelSchema):
    user: UserSchema
    country: Optional[CountrySchema]
    skill: Optional[TalentSkillSchema]
    experience_history: List[ExperienceSchema]
    education_history: List[EducationSchema]
    photo_url: Optional[str]
    cv_url: Optional[str]
    native_language: Optional[LanguageSchema]
    additional_languages: List[LanguageSchema]
    class Meta:
        model = Talent
        exclude = (*READ_EXCLUDE_FIELDS, "cv", "photo")



class CompleteTalentProfileSchema(ModelSchema):
    gender: GenderType
    availability: Optional[MutateTalentAvailabilitySchema]
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


class CompleteTalentProfileSchema3(Schema):
    skill: Optional[MutateTalentSkill]
    experience_history: Optional[List[MutateExperienceSchema]]


