from datetime import date
from typing import List, Optional

from ninja import Schema

from apps.core.schemas import CountrySchema


class SkillSchema(Schema):
    name: Optional[str] = None
    department_id: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    custom: Optional[bool] = None
    uid: Optional[str] = None


class AdditionalSkillSchema(Schema):
    skill: Optional[str] = None
    custom: Optional[bool] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None


class ExperienceHistorySchema(Schema):
    uid: Optional[str] = None
    role: Optional[str] = None
    level: Optional[str] = None
    company: Optional[str] = None
    salary_bonus: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    currently_works_here: Optional[bool] = None


class EducationHistorySchema(Schema):
    uid: Optional[str] = None
    level: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    major: Optional[str] = None
    certification: Optional[str] = None
    university: Optional[str] = None


class ParsedTalentProfileSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    visible: Optional[bool] = None
    preferred_communication: Optional[str] = None
    phone_code: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    viber_number: Optional[str] = None
    country: Optional[CountrySchema] = None
    state: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    availability_timezone: Optional[str] = None

    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    facebook: Optional[str] = None
    twitter_x: Optional[str] = None

    role: Optional[str] = None
    employment_types: Optional[List[str]] = None
    work_models: Optional[List[str]] = None
    business_models: Optional[List[str]] = None

    notice_period: Optional[int] = None
    notice_period_type: Optional[str] = None
    flexible_availability: Optional[bool] = None

    native_language: Optional[str] = None
    additional_languages: Optional[List[str]] = None

    skills: Optional[List[SkillSchema]] = None
    additional_skills: Optional[List[AdditionalSkillSchema]] = None

    education_history: Optional[List[EducationHistorySchema]] = None
    experience_history: Optional[List[ExperienceHistorySchema]] = None
    availability: Optional[List[dict]] = None



class JobDescriptionSchema(Schema):
    job_title: str
    job_description: str
    key_responsibilities: List[str]
    required_qualifications: List[str]
    preferred_qualifications: List[str]
    skills: List[str]
    experience_level: str
    error: Optional[str] = None


    @classmethod
    def example(cls, with_error=False):
        return cls(
            job_title='A sample job',
            job_description="A sample job description",
            key_responsibilities=[
                "A sample key responsibility"
            ],
            required_qualifications=[
                "A sample required qualification"
            ],
            preferred_qualifications=[
                "A sample preferred qualification"
            ],
            skills=[
                "A sample skill"
            ],
            experience_level="A sample experience level",
            error=None if not with_error else "A sample error"
        )

class JobSalaryResponseSchema(Schema):
    hourly_rate_min: float
    hourly_rate_max: float
    annual_salary_min: float
    annual_salary_max: float
    currency: str

    bonus_hourly_rate_min: float
    bonus_hourly_rate_max: float
    bonus_annual_salary_min: float
    bonus_annual_salary_max: float

    @classmethod
    def example(cls):
        return cls(
            hourly_rate_min=45.0,
            hourly_rate_max=85.0,
            annual_salary_min=90000.0,
            annual_salary_max=170000.0,
            currency="USD",

            bonus_hourly_rate_min=5.0,
            bonus_hourly_rate_max=15.0,
            bonus_annual_salary_min=8000.0,
            bonus_annual_salary_max=25000.0
        )


class JobSalaryRequestSchema(Schema):
    job_title: str
    job_description: str
    location: str
    experience_level: str
    skills: List[str]
    industry: str
    employment_type: str