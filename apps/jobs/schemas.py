from ninja import ModelSchema
from ninja.schema import Schema
from datetime import time


class AvailabilitySchema(Schema):
    day: str
    start_time: time
    end_time: time


class CreateJobSchema(ModelSchema):
    employment_type: str
    availability: list[AvailabilitySchema]
    class Meta:
        fields = [
            "hiring_company_name", "hiring_company_description", "work_structure", "technological_requirements", "lunch_breaks",

        ]