from django.conf import settings

from accounts.models import BusinessUser
from jobs.enums import WorkStructureEnum
from jobs.models import JobPost, Job

BASE_FRONTEND_URL = settings.FRONTEND_URL

JOB_POST_URL = lambda job_post_uid: f"{BASE_FRONTEND_URL}/{job_post_uid}"


def get_remote_type(work_structure: WorkStructureEnum):
    if work_structure == WorkStructureEnum.REMOTE.value:
        return "Fully Remote"
    return "Hybrid Remote"

def get_education(job: Job):
    if not job.minimum_education_level:
        "Not Required"
    return job.minimum_education_level.name

def get_experience(job: Job):
    role = job.role.name
    years_of_experience = job.years_of_experience
    if not role and years_of_experience:
        return f"{years_of_experience} years experience is required"
    elif role and not years_of_experience:
        return f"Experience in {role} is required"
    return f"{years_of_experience} years of experience in {role} is required"

def get_job_type(job_post: JobPost):
    job: Job = job_post.job
    if not job.employment_type:
        return "Full-time"
    employment_type:str = str(job.employment_type.name).lower()
    if employment_type.startswith("full-time"):
        return ["5QWDV"]
    elif employment_type.startswith("part-time"):
        return ["75GKK"]
    return ["VDTG7"]


def convert_job_object_to_job(job_post:JobPost):
    job:Job = job_post.job
    business_user: BusinessUser = job_post.job.created_by
    return {
        "sourcePostingId": job_post.indeed_id,
        "body": {
            "title": job.title,
            "description": job.about,
            "location": {
                "country": job_post.country.code,
                "cityRegionPostal": f"{job_post.province} {job_post.postal_code}"
            },
            "benefits": job_post.benefits,
            "salary": {
              "currency": job_post.annual_salary_currency.abbreviation,
              "maximumMinor": job_post.annual_salary_max,
              "minimumMinor": job_post.annual_salary_min,
              "period": "MONTH"
            },
            "hasProbationaryPeriod": "UNKNOWN"
        },
        "metadata": {
            "jobSource": {
                "companyName": job.business_name(),
                "sourceName": "Source",
                "sourceType": "Employer"
            },
            "jobPostingId": str(job_post.uid),
            "datePublished": str(job_post.date_posted),
            "url": JOB_POST_URL(job_post.uid),
            "taxonomyClassification": {
              "jobTypes": get_job_type(job_post),
              "remoteType": get_remote_type(job.work_structure),
              "education": get_education(job_post.job),
              "experience": get_experience(job_post.job)
            },
            "contacts":[
                {
                    "contactType": ["recruiter"],
                    "contactInfo": {
                        "contactEmail": business_user.user.email,
                        "contactName": business_user.business.name,
                        "contactPhone": business_user.user.phone_number
                    }
                }
            ]

        },
        "applyMethod": {
          "postUrl": JOB_POST_URL(job_post.uid),
          "phoneRequired": "NO",
          "coverLetterRequired": "NO",
          "resumeRequired": "NO",
          "nameFormat": "FIRST_LAST_NAME"
        }
    }

def convert_job_object_to_indeed_id(job_post:JobPost):
    return {"sourcedPostingId": job_post.indeed_id}
