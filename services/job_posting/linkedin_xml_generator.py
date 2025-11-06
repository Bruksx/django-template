from xml.etree import ElementTree as ET

from jobs.enums import JobStatusType
from jobs.models import JobPost

from services.job_posting.services.linkedin import job_post_to_job_schema


def generate_job_post_xml()->bytes:
    root = ET.Element("jobs")
    for job in JobPost.objects.select_related("job").filter(
        status=JobStatusType.POSTED.value,
    ).order_by("-refresh_order").iterator(chunk_size=30):
        linkedin_job = job_post_to_job_schema(job)
        root.append(linkedin_job.to_xml())
    return ET.tostring(root, encoding="utf-8", method="xml")


def generate_job_post_xml_stream():
    yield '<?xml version="1.0" encoding="UTF-8"?>\n'
    yield '<jobs>\n'

    queryset = (JobPost.objects
                .select_related(
                    'job',
                    'job__employment_type',
                    'job__department',
                    'job__job_level',
                    'job__minimum_education_level',
                    'job__first_language',
                    'salary_currency',
                    'salary_bonus_currency',
                )
                .prefetch_related(
                    'job__business_models',
                    'job__skills',
                    'job__availableday_set',
                )
                .filter(status=JobStatusType.POSTED.value)
                .order_by("-refresh_order")
                .iterator(chunk_size=500)  # DB-level chunking

            )


    for job in queryset:
            linkedin_job = job_post_to_job_schema(job)
            yield ET.tostring(linkedin_job.to_xml(), encoding="unicode") + "\n"
        yield '</jobs>\n'
