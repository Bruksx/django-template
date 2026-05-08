from dataclasses import dataclass
from datetime import datetime
from html import unescape
from typing import Optional
from xml.sax.saxutils import escape

from core.enums import SalaryType
from htmlmin import minify
from jobs.enums import WorkStructureEnum, JobStatusType
from jobs.models import JobPost, Job
from jobs.schemas import IndeedTalentJobPostSchema
from jobs.schemas import JobAvailabilitySchema
from lxml import etree as et
from lxml.etree import Element, SubElement, tostring

from apps.paginations import CustomPageNumberPaginationExtra
from config import settings
from helpers.utils import alert_bug_via_email, html_to_text

BASE_FRONTEND_URL = settings.FRONTEND_URL
BASE_BACKEND_URL = settings.BACKEND_URL

JOB_POST_URL = lambda job_post_uid: f"{BASE_FRONTEND_URL}jobs-listing/{job_post_uid}?source=Indeed"

SCREENING_QUESTIONS_URL = lambda job_uid: f"{BASE_BACKEND_URL}/business/jobs/{job_uid}/indeed/screener-questions"
INDEED_EMAIL = settings.INDEED_EMAIL
INDEED_APPLY_API_TOKEN = settings.INDEED_APPLY_API_TOKEN
INDEED_APPLY_POST_URL = lambda job_post_uid: f"{BASE_BACKEND_URL}/api/business/jobs/indeed/jobs/{job_post_uid}/apply"

@dataclass
class JobBase:
    title: str
    date: datetime
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
            indeed_apply_postUrl=INDEED_APPLY_POST_URL(self.apijobid)
        )

        params = []

        for key, value in data.items():
            if value is None:
                value = ""
            key = key.replace('_', '-')
            params.append(f"{key}={value}")  # NO escaping

        return "&".join(params)



    @staticmethod
    def _build_description(job_post: JobPost, job: Job) -> str:
        parts = []

        # Title
        parts.append(f"{job.get_title or 'Untitled Role'} at {job.business_name() or 'Company'}\n")


        # About Job
        if job_post.get_about():
            about = job_post.get_about()
            parts.append("ABOUT THE JOB\n")
            parts.append(f"{about.strip()}\n\n")

        # Job Details
        details = []
        if job.employment_type: details.append(f"Employment Type: {job.employment_type.name}")
        if job.department: details.append(f"Department: {job.department.name}")
        if job.job_level: details.append(f"Job Level: {str(job.job_level.name).title()}")
        if job.years_of_experience: details.append(f"Experience: {job.years_of_experience} Years")
        if job.business_models.exists():
            details.append(f"Business Model: {', '.join(bm.name for bm in job.business_models.all())}")
        if job.minimum_education_level: details.append(f"Education: {job.minimum_education_level.level}")
        if job.qualification: details.append(f"Qualification: {job.qualification}")

        if details:
            parts.append("JOB DETAILS\n")
            for d in details:
                parts.append(f"  • {d}\n")
            parts.append("\n")

        # Skills (cached in prefetch)
        skill_map = {"Tools/Platform": [], "Methodologies/Frameworks": [], "General Skills": [], "Soft Skills": []}
        for skill in job.skills.all():
            cat = skill.category.name if skill.category else ""
            if cat in skill_map:
                skill_map[cat].append(skill.name)

        skills_lines = []
        if skill_map["Tools/Platform"]: skills_lines.append(
            f"Tools/Platforms: {', '.join(skill_map['Tools/Platform'])}")
        if skill_map["Methodologies/Frameworks"]: skills_lines.append(
            f"Methodologies/Frameworks: {', '.join(skill_map['Methodologies/Frameworks'])}")
        if skill_map["General Skills"]: skills_lines.append(f"General Skills: {', '.join(skill_map['General Skills'])}")
        if skill_map["Soft Skills"]: skills_lines.append(f"Soft Skills: {', '.join(skill_map['Soft Skills'])}")
        if job.additional_skills:
            skills_lines.append(f"Additional Skills: {', '.join(job.additional_skills)}")

        if skills_lines:
            parts.append("REQUIRED SKILLS\n")
            for s in skills_lines:
                parts.append(f"  • {s}\n")
            parts.append("\n")

        # Responsibilities
        if job.responsibilities:
            parts.append("RESPONSIBILITIES\n")
            parts.append(html_to_text(job.responsibilities))
            parts.append("\n")

        # Salary & Benefits
        salary_parts = []
        if job_post.salary_min and job_post.salary_max:
            cur = job_post.salary_currency.symbol if job_post.salary_currency else "$"
            salary_parts.append(f"Pay: {job_post.salary_type}, {cur} {job_post.salary_min}–{job_post.salary_max}")
        if job_post.salary_bonus_min and job_post.salary_bonus_max:
            cur = job_post.salary_bonus_currency.symbol if job_post.salary_bonus_currency else "$"
            salary_parts.append(
                f"Bonus: {job_post.salary_bonus_type}, {cur} {job_post.salary_bonus_min}–{job_post.salary_bonus_max}")
        if job_post.benefits:
            benefits = ", ".join(job_post.benefits) if isinstance(job_post.benefits, list) else job_post.benefits
            salary_parts.append(f"Benefits: {benefits}")
        if job.lunch_break and job.lunch_break_time:
            salary_parts.append(f"Break: {str(job.lunch_break).title()}, {job.lunch_break_time} mins")

        if salary_parts:
            parts.append("SALARY & BENEFITS\n")
            for s in salary_parts:
                parts.append(f"  • {s}\n")
            parts.append("\n")

        # Working Hours
        if hasattr(job, 'availableday_set') and job.availableday_set.exists():
            parts.append("WORKING HOURS\n")
            for day in job.availableday_set.all().order_by('id'):
                if day.start_time and day.end_time:
                    parts.append(
                        f"  - {day.day}: {day.start_time.strftime('%H:%M')} - {day.end_time.strftime('%H:%M')}\n")
                else:
                    parts.append(f"  - {day.day}: Available\n")
            parts.append("\n")

        # Tech + Language
        extra = []
        if job.technological_requirement:
            if str(job.technological_requirement).lower().startswith("either"):
                value = "Windows or Mac"
            else:
                value = str(job.technological_requirement).title()
            extra.append(f"Tech Requirements: {value}")
        if job.first_language:
            extra.append(f"Language: {job.first_language.name}")
        if extra:
            parts.append("ADDITIONAL REQUIREMENTS\n")
            for e in extra:
                parts.append(f"  • {e}\n")
            parts.append("\n\n")

        # About Company
        if job.hiring_company_description:
            parts.append("ABOUT THE COMPANY\n")
            parts.append(f"{job.hiring_company_description.strip()}\n\n")

        # Apply Link
        parts.append(f"APPLY NOW: {JOB_POST_URL(job_post.uid)}")


        return "".join(parts)
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
    def _format_working_hours(job: Job):
        """Format working hours/available days for display in Indeed description"""
        from jobs.schemas import JobAvailableDaySchema

        available_days = job.availableday_set.all().order_by('id')
        if available_days.count() == 0:
            return None

        formatted_hours = []
        for availability in available_days:
            if availability.start_time and availability.end_time:
                # Format time as HH:MM
                start = availability.start_time.strftime('%H:%M')
                end = availability.end_time.strftime('%H:%M')
                formatted_hours.append(f"{availability.day}: {start} - {end}")
            else:
                formatted_hours.append(f"{availability.day}: Available")

        return formatted_hours if formatted_hours else None

    @staticmethod
    def get_job_html_description(job_post):
        from django.template.loader import render_to_string
        return minify(render_to_string("jobs/en/indeed_job_desc.html", IndeedTalentJobPostSchema.from_orm(job_post).dict() ),remove_empty_space=True, remove_comments=True)

    @staticmethod
    def get_description(job_post: JobPost, job: Job) -> str:
        parts = []

        # Title
        parts.append(f"{job.get_title or 'Untitled Role'} at {job.business_name() or 'Company'}\n")

        # About Company
        if job.hiring_company_description:
            parts.append("ABOUT THE COMPANY\n")
            parts.append(f"{job.hiring_company_description.strip()}\n\n")

        # About Job
        if job_post.get_about():
            about = job_post.get_about()
            parts.append("ABOUT THE JOB\n")
            parts.append(f"{about.strip()}\n\n")

        # Job Details
        details = []
        if job.employment_type: details.append(f"Employment Type: {job.employment_type.name}")
        if job.department: details.append(f"Department: {job.department.name}")
        if job.job_level: details.append(f"Job Level: {job.job_level.name}")
        if job.years_of_experience: details.append(f"Experience: {job.years_of_experience} Years")
        if job.business_models.exists():
            details.append(f"Business Model: {', '.join(bm.name for bm in job.business_models.all())}")
        if job.minimum_education_level: details.append(f"Education: {job.minimum_education_level.level}")
        if job.qualification: details.append(f"Qualification: {job.qualification}")

        if details:
            parts.append("JOB DETAILS\n")
            for d in details:
                parts.append(f"  • {d}\n")
            parts.append("\n")

        # Skills (cached in prefetch)
        skill_map = {"Tools/Platform": [], "Methodologies/Frameworks": [], "General Skills": [], "Soft Skills": []}
        for skill in job.skills.all():
            cat = skill.category.name if skill.category else ""
            if cat in skill_map:
                skill_map[cat].append(skill.name)

        skills_lines = []
        if skill_map["Tools/Platform"]: skills_lines.append(
            f"Tools/Platforms: {', '.join(skill_map['Tools/Platform'])}")
        if skill_map["Methodologies/Frameworks"]: skills_lines.append(
            f"Methodologies/Frameworks: {', '.join(skill_map['Methodologies/Frameworks'])}")
        if skill_map["General Skills"]: skills_lines.append(f"General Skills: {', '.join(skill_map['General Skills'])}")
        if skill_map["Soft Skills"]: skills_lines.append(f"Soft Skills: {', '.join(skill_map['Soft Skills'])}")
        if job.additional_skills:
            skills_lines.append(f"Additional Skills: {', '.join(job.additional_skills)}")

        if skills_lines:
            parts.append("REQUIRED SKILLS\n")
            for s in skills_lines:
                parts.append(f"  • {s}\n")
            parts.append("\n")

        # Responsibilities
        if job.responsibilities:
            parts.append("RESPONSIBILITIES\n")
            parts.append(html_to_text(job.responsibilities))
            parts.append("\n")

        # Salary & Benefits
        salary_parts = []
        if job_post.salary_min and job_post.salary_max:
            cur = job_post.salary_currency.symbol if job_post.salary_currency else "$"
            salary_parts.append(f"Pay: {job_post.salary_type} • {cur} {job_post.salary_min}–{job_post.salary_max}")
        if job_post.salary_bonus_min and job_post.salary_bonus_max:
            cur = job_post.salary_bonus_currency.symbol if job_post.salary_bonus_currency else "$"
            salary_parts.append(
                f"Bonus: {job_post.salary_bonus_type} • {cur} {job_post.salary_bonus_min}–{job_post.salary_bonus_max}")
        if job_post.benefits:
            benefits = ", ".join(job_post.benefits) if isinstance(job_post.benefits, list) else job_post.benefits
            salary_parts.append(f"Benefits: {benefits}")
        if job.lunch_break and job.lunch_break_time:
            salary_parts.append(f"Break: {job.lunch_break} • {job.lunch_break_time} mins")

        if salary_parts:
            parts.append("SALARY & BENEFITS\n")
            for s in salary_parts:
                parts.append(f"  • {s}\n")
            parts.append("\n")

        # Working Hours
        if hasattr(job, 'availableday_set') and job.availableday_set.exists():
            parts.append("WORKING HOURS\n")
            for day in job.availableday_set.all().order_by('id'):
                if day.start_time and day.end_time:
                    parts.append(
                        f"  - {day.day}: {day.start_time.strftime('%H:%M')} - {day.end_time.strftime('%H:%M')}\n")
                else:
                    parts.append(f"  - {day.day}: Available\n")
            parts.append("\n")

        # Tech + Language
        extra = []
        if job.technological_requirement:
            extra.append(f"Tech Requirements: {job.technological_requirement}")
        if job.first_language:
            extra.append(f"Language: {job.first_language.name}")
        if extra:
            parts.append("ADDITIONAL REQUIREMENTS\n")
            for e in extra:
                parts.append(f"  • {e}\n")
            parts.append("\n")

        return "".join(parts)
    @staticmethod
    def get_education(job_post: JobPost):
        if not job_post.job.minimum_education_level:
            return "Bachelors"
        return job_post.job.minimum_education_level.level

    @classmethod
    def convert_to_job(cls, job_post):
        job: Job = job_post.job
        return JobBase(
                title=job_post.job.get_title,
                date=job_post.date_posted or job_post.created_at,
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
                streetaddress=job_post.get_location(),
                email=INDEED_EMAIL,
                description=cls.get_job_html_description(job_post),
                salary=JobBase.get_salary(job_post),
                education=JobBase.get_education(job_post),
                jobtype="".join((job.employment_type.name,)) if job.employment_type else "",
                experience=f"{job.years_of_experience} years" if job.years_of_experience else job.years_of_experience,
                lastactivitydate=job_post.last_refreshed or job_post.created_at,
                remotetype="Fully remote" if job_post.job.work_structure == WorkStructureEnum.REMOTE.value else "Hybrid remote",
                apijobid=str(job_post.uid)
            )

    @staticmethod
    def add_element(parent, tag: str, text: str, escape_text: bool = False, omit_cdata: bool = False):
        el = SubElement(parent, tag)
        if text and str(text).strip():
            content = str(text).strip()
            if escape_text is False:
                content = unescape(content)
        else:
            content = ""
        if omit_cdata is True:
            el.text = content
        else:
            #el.text = f"<![CDATA[{content}]]>"
            el.text = et.CDATA(content)

    def to_xml(self):
        job_el = Element( "job")
        self.add_element(job_el, "title", self.title)
        self.add_element(job_el, "date", self.date.isoformat())
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
    def add_element(parent, tag: str, text: Optional[str]):
        """Adds a safe XML element, escaping special characters."""
        if text and str(text).strip():
            el = SubElement(parent, tag)
            el.text = f"<![CDATA[{text.strip()}]]>"

    @staticmethod
    def to_xml_stream(page=None, page_size=None):
        """
        the pagination is for debugging
        """
        yield '<?xml version="1.0" encoding="UTF-8"?>\n'
        yield '<source>\n'
        yield '<publisher>1840 GTC</publisher>\n'
        yield f'<publisherurl>{escape(BASE_FRONTEND_URL)}</publisherurl>\n'

        if page and page_size:
            pagination = CustomPageNumberPaginationExtra(page_size)
            queryset = pagination.get_paginated_queryset(
                queryset=(
                JobPost.objects
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
            ), pagination=pagination.Input(page=page, page_size=page_size)
            )
        else:
            queryset = (
                JobPost.objects
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
        for job_post in queryset:
            job_base = alert_bug_via_email(JobBase.convert_to_job, job_post=job_post, default=None)
            if job_base:
                xml = alert_bug_via_email(job_base.to_xml, default=None)
                if xml:
                    yield tostring(xml, encoding="unicode") + "\n"
        yield '</source>\n'
