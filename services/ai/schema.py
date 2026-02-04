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