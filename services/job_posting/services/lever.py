from enum import Enum

import requests

from accounts.models import Business
from jobs.enums import JobStatusType, WorkStructureEnum
from jobs.models import JobPost, Job

from core.enums import SalaryType
from helpers.loggers import Logger, LogSchema

BASE_URL = "https://api.lever.co/v1"
API_KEY = ""
USER_ID = ""


class TriggerType(Enum):
    BUSINESS = "Business"
    JOB_POST = "JobPost"
    JOB = "Job"

TRIGGER_FIELDS = {
    TriggerType.BUSINESS: ("website",),
    TriggerType.JOB: ("title", "department", "about", "responsibilities", "work_structure",
                  "employment_type"),
    TriggerType.JOB_POST: ("country", "salary_max", "salary_min", "salary_currency",
                       "benefits", "status")
}


def create_description_html(job_post:JobPost):
    job:Job = job_post.job
    body = list()
    if job.title:
        body.append(f"<div>The <u><b>{job.title}</b></u></div>")
    if job.about:
        body.append(f"<div>{job.about}</div>")
    return "".join(body)

def create_lists(job_post:JobPost):
    job:Job = job_post.job
    lists = list()
    if job.responsibilities:
        lists.append(
            {
                "text": "Responsibilities",
                "context" : "".join([
                    f"<li>{res}</li>"
                    for res in job.responsibilities
                ])
            }
        )
    if job_post.benefits:
        lists.append(
            {
                "text": "Benefits",
                "context": "".join([
                    f"<li>{benefit}</li>"
                    for benefit in job_post.benefits
                ])
            }
        )
    return lists


def handle_job_stage(job_post: JobPost):
    choices = {
        JobStatusType.DRAFT: "draft",
        JobStatusType.CLOSED: "closed",
        JobStatusType.PAUSED: "pending",
        JobStatusType.POSTED: "published"
    }
    return choices.get(job_post.status, "draft")

def handle_job_work_place(job_post: JobPost):
    job: Job = job_post.job

    choices = {
        WorkStructureEnum.REMOTE: "remote",
        WorkStructureEnum.HYBRID: "hybrid",
        WorkStructureEnum.IN_OFFICE: "onsite"
    }
    return choices.get(job.work_structure, "onsite")

def handle_job_commitment(job_post: JobPost):
    job: Job = job_post.job
    if not job.employment_type:
        return "Full-time"
    employment_type:str = str(job.employment_type.name).lower()
    if employment_type.startswith("full-time"):
        return "Full-time"
    elif employment_type.startswith("part-time"):
        return "Part-time"
    else:
        return "Internship"

def has_new_update(previous_object, new_object, trigger_type: TriggerType):
    fields = TRIGGER_FIELDS.get(trigger_type)
    for field in fields:
        if getattr(previous_object, field) != getattr(new_object, field):
            return True
    return False

def get_posts_on_trigger(new_object, trigger_type: TriggerType):
    if trigger_type == TriggerType.BUSINESS:
        return JobPost.objects.filter(job__created_by__business=new_object)
    elif trigger_type == TriggerType.JOB_POST:
        return JobPost.objects.filter(id=new_object.id)
    elif trigger_type == TriggerType.JOB:
        return JobPost.objects.filter(job=new_object)
    return JobPost.objects.none()


def handle_update(job_posts):
    for job_post in job_posts:
        if job_post.lever:
            update_job_post(job_post)
        else:
            create_job_post(job_post)
    return

def deploy_jobs(previous_object, new_object, trigger_type: TriggerType):
    # this would called on signals
    has_update = has_new_update(previous_object, new_object, trigger_type)
    if not has_update:
        return
    handle_update(get_posts_on_trigger(new_object, trigger_type))
    return


def get_salary(currency, salary_type, salary_value):

    period = {
        SalaryType.HOURLY.value: "hour",
        SalaryType.DAILY.value: "day",
        SalaryType.BI_WEEKLY.value: "week",
        SalaryType.BI_MONTHLY.value: "month",
        SalaryType.WEEKLY.value: "week",
        SalaryType.MONTHLY.value: "month",
        SalaryType.ANNUALLY.value: "year",

    }
    if salary_type in (SalaryType.BI_WEEKLY.value, SalaryType.BI_MONTHLY.value) and salary_value:
        if type(salary_value) == tuple:
            salary_value = map(lambda x: x / 2, salary_value)
        else:
            salary_value /= 2
    if type(salary_value) != tuple:
        salary_value = (salary_value, salary_value)
    return {
        "currency": currency,
        "max": salary_value[1],
        "min": salary_value[0],
        "interval": f"per-{period.get(salary_type, 'year')}-salary"

    }


def create_job_post(job_post:JobPost):
    url = f"{BASE_URL}/postings"
    headers = {
        "API_KEY": API_KEY,
        "Content-Type": "application/json"
    }
    job:Job = job_post.job
    company:Business = job.created_by.business
    data = {
          "text": job.title,
          "owner": USER_ID,
          "hiringManager": USER_ID,
          "categories": {
            "team": "Platform",
            "department": job.department.name,
            "location": job_post.country.name,
            "commitment": handle_job_commitment(job_post),
            "allLocations": [
              job_post.country.name
            ]
          },
          "content": {
            "descriptionHtml": create_description_html(job_post),
            "lists": create_lists(job_post),
            "closingPostingHtml": f"<div>Our <a href=\"{company.website}\">company</a> is <span>proud</span> to be an equal opportunity workplace.</div>"
          },
          "distributionChannels": [
            "internal",
            "public"
          ],
          "salaryDescriptionHtml": "<p>This is a salary description.</p>",
          "salaryRange": get_salary(job_post.salary_currency.name, job_post.salary_type,
                                    (job_post.salary_min, job_post.salary_max)),
          "state": handle_job_stage(job_post),
          "tags": [
            "engineering",
            "high-priority"
          ],
          "workplaceType": handle_job_work_place(job_post)
        }

    response = requests.post(url=url, headers=headers, json=data)
    if response.status_code != 201:
        Logger.error(LogSchema(
            sender="Lever Service",
            description=str(response.content),
            title="Job creation failed"
        ).__dict__, exc_info=True)
    lever_data = {}
    data = response.json()
    lever_data["urls"] = data["urls"]
    lever_data["id"] = data["id"]
    job_post.lever = lever_data
    job_post.save()

def update_job_post(job_post):
    job: Job = job_post.job
    company: Business = job.created_by.business
    lever_data = job_post.lever
    url = f"{BASE_URL}/postings/{lever_data['id']}?perform_as={USER_ID}"
    headers = {
        "API_KEY": API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": job.title,
        "owner": USER_ID,
        "hiringManager": USER_ID,
        "categories": {
            "team": "Platform",
            "department": job.department.name,
            "location": job_post.country.name,
            "commitment": handle_job_commitment(job_post),
            "allLocations": [
                job_post.country.name
            ]
        },
        "content": {
            "descriptionHtml": create_description_html(job_post),
            "lists": create_lists(job_post),
            "closingPostingHtml": f"<div>Our <a href=\"{company.website}\">company</a> is <span>proud</span> to be an equal opportunity workplace.</div>"
        },
        "distributionChannels": [
            "internal",
            "public"
        ],
        "salaryDescriptionHtml": "<p>This is a salary description.</p>",
        "salaryRange": get_salary(job_post.salary_currency.name, job_post.salary_type,
                                    (job_post.salary_min, job_post.salary_max)),
        "state": handle_job_stage(job_post),
        "tags": [
            "engineering",
            "high-priority"
        ],
        "workplaceType": handle_job_work_place(job_post)
    }

    response = requests.post(url=url, headers=headers, json=data)
    if response.status_code != 201:
        Logger.error(LogSchema(
            sender="Lever Service",
            description=str(response.content),
            title="Job update failed"
        ).__dict__, exc_info=True)
    return
