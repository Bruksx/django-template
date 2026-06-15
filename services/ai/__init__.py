from services.ai.client import GtcAiClient
from services.ai.schema import ParsedTalentProfileSchema
from services.ai.schema import JobDescriptionSchema, JobSalaryRequestSchema, JobSalaryResponseSchema

from services.ai.schema import ParsedTalentProfileSchema



def generate_job_description(prompt: str=None, file_url: str=None)->JobDescriptionSchema:
    client = GtcAiClient()
    response = client.post(
        "v1/jobs/generate-description",
        json={"url": file_url, "job_input": prompt},
    )
    return JobDescriptionSchema(**response.json())


def parse_cv(cv_url: str):
    client = GtcAiClient()
    response = client.post(
        "accounts/talents/profile/cv/parse",
        params={"url": cv_url},
    )
    return response.json()


def generate_job_post_salary(data: JobSalaryRequestSchema)->JobSalaryResponseSchema:
    client = GtcAiClient()
    response = client.post(
        "v1/jobs/generate-salary",
        json=data.dict()
    )
    return JobSalaryResponseSchema(**response.json())


def run_batch():
    client = GtcAiClient()
    response = client.post(
        "v1/match/run-batch",
        {"reembed_all":False}
    )
    return response.json()