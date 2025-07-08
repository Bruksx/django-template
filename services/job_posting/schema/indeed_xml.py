from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring


from config import settings
from jobs.enums import WorkStructureEnum, JobStatusType
from jobs.models import JobPost, Job

from helpers.loggers import Logger

BASE_FRONTEND_URL = settings.FRONTEND_URL
BASE_BACKEND_URL = settings.BACKEND_URL

JOB_POST_URL = lambda job_post_uid: f"{BASE_FRONTEND_URL}/job-details/{job_post_uid}"

SCREENING_QUESTIONS_URL = lambda job_uid: f"{BASE_BACKEND_URL}/business/jobs/{job_uid}/indeed/screener-questions"
INDEED_EMAIL = settings.INDEED_EMAIL



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

    @staticmethod
    def get_salary(job_post: JobPost):
        currency = job_post.annual_salary_currency
        currency = currency.symbol if currency else "$"
        if job_post.annual_salary_min and not job_post.annual_salary_max:
            return f"{currency}{job_post.annual_salary_min} per month"
        if not job_post.annual_salary_min and job_post.annual_salary_max:
            return f"{currency}{job_post.annual_salary_max} per month"
        if job_post.annual_salary_min and job_post.annual_salary_max:
            return f"{currency}{job_post.annual_salary_min}-{currency}{job_post.annual_salary_max} per month"
        return f"{currency} 0 per month"

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
                city=job_post.city,
                state=job_post.province,
                country=job_post.country.name,
                postalcode=job_post.postal_code,
                streetaddress=job_post.city,
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
            filter(status=JobStatusType.POSTED.value).order_by("-created_at").iterator():
            try:
                job_base = JobBase.convert_to_job(job_post)
                yield tostring(job_base.to_xml(), encoding="unicode") + "\n"
            except Exception as e:
                Logger.critical(msg={"sender": "Indeed Job Posting service", "title": "Indeed Job Posting service Error", "description": str(e)},
                                exc_info=True)


        yield '</source>\n'

