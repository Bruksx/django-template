from typing import List, Optional
from datetime import date
from ninja import Schema
from uuid import UUID


class SkillSchema(Schema):
    name: Optional[str] = None
    department_id: Optional[str] = None
    category_id: Optional[str] = None
    custom: Optional[bool] = None
    uid: Optional[str] = None


class AdditionalSkillSchema(Schema):
    skill: Optional[str] = None
    custom: Optional[bool] = None
    category_id: Optional[str] = None


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
    country: Optional[str] = None
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