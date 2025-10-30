from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus
from xml.etree.ElementTree import Element, SubElement, tostring

from apps.core.enums import SalaryType
from config import settings
from jobs.enums import WorkStructureEnum, JobStatusType
from jobs.models import JobPost, Job

from helpers.loggers import Logger

BASE_FRONTEND_URL = settings.FRONTEND_URL
BASE_BACKEND_URL = settings.BACKEND_URL

JOB_POST_URL = lambda job_post_uid: f"{BASE_FRONTEND_URL}job-details/{job_post_uid}"

SCREENING_QUESTIONS_URL = lambda job_uid: f"{BASE_BACKEND_URL}/business/jobs/{job_uid}/indeed/screener-questions"
INDEED_EMAIL = settings.INDEED_EMAIL
INDEED_APPLY_API_TOKEN = settings.INDEED_APPLY_API_TOKEN
INDEED_APPLY_POST_URL = lambda job_post_uid: f"{BASE_BACKEND_URL}/api/business/jobs/indeed/jobs/{job_post_uid}/apply"
INDEED_APPLY_QUESTION_URL = f"{BASE_BACKEND_URL}/api/business/jobs/indeed/apply-questions"


@dataclass
class JobBase:
    title: str
    date: str
    referencenumber: str
    requisitionid: str
    url: str
    company: str
    sourcename: str
    city: str
    state: str
    country: str
    postalcode: str
    streetaddress: str
    email: str
    description: str
    salary: str
    education: str
    jobtype: str
    experience: str
    lastactivitydate: datetime
    category: Optional[str] = None
    expirationdate: Optional[str] = None
    remotetype: Optional[str] = None
    billingId: Optional[str] = None
    apijobid: Optional[str] = None
    location: Optional[str] =   None


    def get_indeed_apply_data(self):

        data = dict(
            indeed_apply_apiToken=INDEED_APPLY_API_TOKEN,
            indeed_apply_jobTitle=self.title,
            indeed_apply_jobId=self.apijobid,
            indeed_apply_jobCompanyName=self.company,
            indeed_apply_jobLocation=self.location,
            indeed_apply_jobUrl=self.url,
            indeed_apply_postUrl=INDEED_APPLY_POST_URL(self.apijobid),
            indeed_apply_questions=INDEED_APPLY_QUESTION_URL
        )
        params = []

        for key, value in data.items():
            key = key.replace('_', '-')
            encoded_value = quote_plus(value)  # URL encode the value
            params.append(f"{key}={encoded_value}")

        return "&".join(params)


    @staticmethod
    def get_indeed_period(salary_type, salary_value):

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
        if type(salary_value) == tuple:
            return f"{salary_value[0]}-{salary_value[1]} per {period.get(salary_type, 'mile')}"
        return f"{salary_value} per {period.get(salary_type, 'mile')}"

    @classmethod
    def get_salary(cls, job_post: JobPost):
        currency = job_post.salary_currency
        currency = currency.symbol if currency else "$"
        if job_post.salary_min and not job_post.salary_max:
            return f"{currency}{cls.get_indeed_period(job_post.salary_type, job_post.salary_min)}"
        if not job_post.salary_min and job_post.salary_max:
            return f"{currency}{cls.get_indeed_period(job_post.salary_type, job_post.salary_max)}"
        if job_post.salary_min and job_post.salary_max:
            return f"{currency}{cls.get_indeed_period(job_post.salary_type, (job_post.salary_min, job_post.salary_max))}"
        return f"{currency} 0 per year"

    @staticmethod
    def get_description(job_post: JobPost):
        return f"""<h2 id="job_description">Job Description: <br><p>{job_post.job.about}</p></h2>"""

    @staticmethod
    def get_education(job_post: JobPost):
        if not job_post.job.minimum_education_level:
            return "Bachelors"
        return job_post.job.minimum_education_level.level

    @classmethod
    def convert_to_job(cls, job_post):
        job: Job = job_post.job
        return JobBase(
                title=job_post.job.title,
                date=str(job_post.date_posted),
                referencenumber=str(job_post.uid),
                requisitionid=str(job_post.uid),
                url=JOB_POST_URL(job_post.uid),
                company=job.business_name(),
                sourcename=job.business_name(),
                location=job_post.get_location(),
                city=job_post.get_city(),
                state=job_post.get_province(),
                country=job_post.get_country(),
                postalcode=job_post.postal_code,
                streetaddress=job_post.get_city(),
                email=INDEED_EMAIL,
                description=JobBase.get_description(job_post),
                salary=JobBase.get_salary(job_post),
                education=JobBase.get_education(job_post),
                jobtype="".join((job.employment_type.name,)) if job.employment_type else "",
                experience=f"{job.years_of_experience} years" if job.years_of_experience else job.years_of_experience,
                lastactivitydate=job_post.date_posted,
                remotetype="Fully remote" if job_post.job.work_structure == WorkStructureEnum.REMOTE else "Hybrid remote",
                apijobid=str(job_post.uid)
            )

    @staticmethod
    def add_element(parent, tag: str, text: str):
        if text:
            el = SubElement(parent, tag)
            el.text = f"<![CDATA[{text}]]>"

    def to_xml(self):
        job_el = Element( "job")
        self.add_element(job_el, "title", self.title)
        self.add_element(job_el, "date", self.date)
        self.add_element(job_el, "referencenumber", self.referencenumber)
        self.add_element(job_el, "requisitionid", self.requisitionid)
        self.add_element(job_el, "url", self.url)
        self.add_element(job_el, "company", self.company)
        self.add_element(job_el, "sourcename", self.sourcename)
        self.add_element(job_el, "city", self.city)
        self.add_element(job_el, "state", self.state)
        self.add_element(job_el, "country", self.country)
        self.add_element(job_el, "postalcode", self.postalcode)
        self.add_element(job_el, "streetaddress", self.streetaddress)
        self.add_element(job_el, "email", self.email)
        self.add_element(job_el, "description", self.description)
        self.add_element(job_el, "salary", self.salary)
        self.add_element(job_el, "education", self.education)
        self.add_element(job_el, "jobtype", self.jobtype)
        self.add_element(job_el, "experience", self.experience)
        self.add_element(job_el, "expirationdate", self.expirationdate)
        self.add_element(job_el, "lastactivitydate", self.lastactivitydate.isoformat())

        if self.category:
            self.add_element(job_el, "category", self.category)

        # Optional fields
        if self.remotetype:
            self.add_element(job_el, "remotetype", self.remotetype)
        if self.billingId:
            self.add_element(job_el, "billingId", self.billingId)
        if self.apijobid:
            self.add_element(job_el, "apijobid", self.apijobid)
        self.add_element(job_el, "indeed-apply-data", self.get_indeed_apply_data())
        return job_el


@dataclass
class Source:
    publisher: Optional[str] = None
    publisherurl: Optional[str] = None

    @classmethod
    def get_data(cls):
        return cls(
            publisher="1840 GTC",
            publisherurl="https://1840gtc.netlify.app",
        )


    @staticmethod
    def add_element(parent, tag: str, text: str):
        if text:
            el = SubElement(parent, tag)
            el.text = f"<![CDATA[{text}]]>"

    @staticmethod
    def to_xml_stream():
        yield '<?xml version="1.0" encoding="UTF-8"?>\n'
        yield '<source>\n'
        yield '<publisher>1840 GTC</publisher>\n'
        yield f'<publisherurl>{BASE_FRONTEND_URL}</publisherurl>\n'

        for job_post in JobPost.objects.select_related("job").\
            filter(status=JobStatusType.POSTED.value).order_by("-refresh_order").iterator():
            try:
                job_base = JobBase.convert_to_job(job_post)
                yield tostring(job_base.to_xml(), encoding="unicode") + "\n"
            except Exception as e:
                Logger.critical(msg={"sender": "Indeed Job Posting service", "title": "Indeed Job Posting service Error", "description": str(e)},
                                exc_info=True)


        yield '</source>\n'

