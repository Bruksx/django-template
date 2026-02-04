from services.ai.client import GtcAiClient
from services.ai.schema import JobDescriptionSchema

def generate_job_description(prompt: str=None, file_url: str=None)->JobDescriptionSchema:
    client = GtcAiClient()
    response = client.post(
        "v1/jobs/generate-description",
        json={"url": file_url, "job_input": prompt},
    )
    return JobDescriptionSchema(**response.json())

