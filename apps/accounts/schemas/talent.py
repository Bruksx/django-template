from locale import currency
from typing import Optional, List, Any

from ninja import Schema, ModelSchema
from ninja.types import DictStrAny

from accounts.enums import GenderType, PreferredCommunicationType
from accounts.models import (Talent, User, TalentAvailability, Education,
                             Experience, TalentSkill, Skill, EducationLevel, Country)
from core.models import Language
from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS
from jobs.schemas import JobLevelSchema, EmploymentTypeSchema


class MutateEducationSchema(ModelSchema):
    level_id: int
    class Meta:
        model = Education
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent", "level"]

class CountrySchema(ModelSchema):
    class Meta:
        model = Country
        exclude = READ_EXCLUDE_FIELDS

class LanguageSchema(ModelSchema):
    class Meta:
        model = Language
        exclude = READ_EXCLUDE_FIELDS

class EducationLevelSchema(ModelSchema):
    class Meta:
        model = EducationLevel
        exclude = [*READ_EXCLUDE_FIELDS]

class EducationSchema(ModelSchema):
    level: EducationLevelSchema

    class Meta:
        model = Education
        exclude = [*READ_EXCLUDE_FIELDS, "talent"]


class MutateExperienceSchema(ModelSchema):
    annual_salary_bonus_currency_id: int
    annual_salary_currency_id: int
    employment_type_id:int
    level_id: int
    class Meta:
        model = Experience
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent", "annual_salary_currency",
                   "annual_salary_bonus_currency", "level",
                   "employment_type"]

class ExperienceSchema(ModelSchema):
    level: JobLevelSchema
    employment_type: EmploymentTypeSchema
    class Meta:
        model = Experience
        exclude = [*READ_EXCLUDE_FIELDS, "talent"]

class MutateTalentSkill(ModelSchema):
    additional_skills:List[str]
    class Meta:
        model = TalentSkill
        exclude = [*MUTATE_EXCLUDE_FIELDS,"talent"]



class SkillSchema(ModelSchema):
    class Meta:
        model = Skill
        exclude = [*READ_EXCLUDE_FIELDS]


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
        exclude = [*MUTATE_EXCLUDE_FIELDS, "talent"]

class ValidateTalentOTPSchema(Schema):
    email: str
    otp: str
    first_name: str
    last_name: str
    preferred_communication: PreferredCommunicationType
    phone_number: str
    country_id: int
    state: str
    city: str
    postal_code: str
    password: str


class UserSchema(ModelSchema):
    token: str
    class Meta:
        model = User
        fields = ["uid", "email", "first_name", "last_name", "phone_number",
                  "gender"]


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
    education_history: List[MutateEducationSchema] = []
    cv: Optional[str] = None
    native_language_id: int


    class Meta:
        model = Talent
        fields = ["cv", "additional_languages"]


class CompleteTalentProfileSchema3(Schema):
    skill: MutateTalentSkill
    experience_history: List[MutateExperienceSchema]


