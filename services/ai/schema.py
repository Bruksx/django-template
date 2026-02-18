from typing import List, Optional
from datetime import date
from ninja import Schema
from uuid import UUID
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



class GenericNameUIDSchema(Schema):
    name: str
    uid: UUID


class JobSkillSchema(GenericNameUIDSchema):
    category_name: str
    department_id: int

class JobDescriptionSchema(Schema):
    role: GenericNameUIDSchema
    job_description: str
    responsibilities: List[str]
    skills: List[JobSkillSchema]
    job_level: GenericNameUIDSchema
    additional_skills: List[str]
    error: Optional[str] = None
    @classmethod
    def example(cls, with_error=False):
        from accounts.models import Skill
        return cls(
            role=GenericNameUIDSchema(name="A sample job", uid=UUID(int=1)),
            job_description="A sample job description",
            responsibilities=[
                "A sample key responsibility"
            ],
            skills=[
                JobSkillSchema(name=skill.name, uid=skill.uid, category_name=skill.category.name, department_id=skill.department_id)
               for skill in Skill.objects.all()[:5]
            ],
            job_level=GenericNameUIDSchema(name="VP of Engineering", uid=UUID(int=5)),
            additional_skills=[
                "A sample additional skill"
            ],
            error=None if not with_error else "A sample error"
        )

    def get_skills(self):
        from accounts.models import SkillCategory, Department
        data = {category: [] for category in SkillCategory.objects.values_list("name", flat=True)}
        for skill in self.skills:
            department = GenericNameUIDSchema.from_orm(Department.objects.filter(id=skill.department_id).first()).dict()
            data[skill.category_name].append(dict(name=skill.name, uid=str(skill.uid), department= department))
        return [{"category": category, "skills": skills} for category, skills in data.items()]

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
    industry: str
    employment_type: str