from typing import List, Optional
from uuid import UUID

from ninja import Schema


class GenericNameUIDSchema(Schema):
    name: str
    uid: UUID

class SkillSchema(GenericNameUIDSchema):
    category_name: str
    department_id: int

class JobDescriptionSchema(Schema):
    role: GenericNameUIDSchema
    job_description: str
    responsibilities: List[str]
    skills: List[SkillSchema]
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
                SkillSchema(name=skill.name, uid=skill.uid, category_name=skill.category.name, department_id=skill.department_id)
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