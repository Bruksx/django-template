from ninja import ModelSchema
from ninja.schema import Schema
from datetime import time
from uuid import UUID
from .models import EmploymentType, Job
from typing import List


class AvailabilitySchema(Schema):
    day: str
    start_time: time
    end_time: time


class CreateJobSchema(ModelSchema):
    employment_type: str
    availability: list[AvailabilitySchema]
    class Meta:
        model = Job
        fields = [
            "hiring_company_name", "hiring_company_description", "work_structure",

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