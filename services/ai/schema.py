from typing import List, Optional

from ninja import Schema


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