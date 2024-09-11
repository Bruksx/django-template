from ninja import ModelSchema
from ninja.schema import Schema
from datetime import time
from uuid import UUID
from .models import EmploymentType, Job, JobPost, ScreeningQuestion, QuestionOption
from typing import List
from .enums import WorkStructureEnum, TechnologicalRequirementsEnum, LunchBreakEnum, QuestionTypeEnum


class AvailabilitySchema(Schema):
    day: str
    start_time: time
    end_time: time


class JobPostSchema(ModelSchema):
    country: str

    class Meta:
        model = JobPost
        fields = ["location_type", "province", "postal_code"]


class QuestionOptionSchema(ModelSchema):
    class Meta:
        model = QuestionOption
        fields = ["is_accepted", "text"]


class QuestionSchema(ModelSchema):
    type: QuestionTypeEnum
    options: List[QuestionOptionSchema]
    class Meta:
        model = ScreeningQuestion
        fields = ["type", "text"]


class CreateJobSchema(ModelSchema):
    employment_type: str
    availability: list[AvailabilitySchema]
    work_structure: WorkStructureEnum
    technological_requirements: TechnologicalRequirementsEnum
    first_language_uid: UUID
    additional_languages: List[UUID]
    lunch_break: LunchBreakEnum
    job_posts: List[JobPostSchema]
    recruiter_uid: UUID
    annual_salary_min: float
    annual_salary_max: float
    annual_bonus_min: float
    annual_bonus_max: float
    same_recruiter: bool
    screening_questions: List[QuestionSchema]

    class Meta:
        model = Job
        fields = [
            "hiring_company_name", "hiring_company_description", "work_structure", "office_address","lunch_break", 
            "additional_hours_min", "additional_hours_max", "annual_salary_min", "annual_salary_max",
            "annual_salary_currency", "annual_bonus_min", "annual_bonus_max", "annual_bonus_currency", "benefits",
            "share_compensation",
        ]


class EmploymentSubTypeSchema(Schema):
    uid: UUID
    name: str


class EmploymentTypeSchema(Schema):
    uid: UUID
    name: str
    sub_types: List[EmploymentSubTypeSchema]
    
    @staticmethod
    def resolve_sub_types(obj):
        return EmploymentType.objects.filter(parent=obj)