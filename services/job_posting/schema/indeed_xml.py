from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.sax.saxutils import escape

from core.enums import SalaryType
from jobs.enums import WorkStructureEnum, JobStatusType
from jobs.models import JobPost, Job
from jobs.schemas import JobAvailabilitySchema

from apps.paginations import CustomPageNumberPaginationExtra
from config import settings
from helpers.email.utils import render_html_email
from helpers.utils import alert_bug_via_email

BASE_FRONTEND_URL = settings.FRONTEND_URL
BASE_BACKEND_URL = settings.BACKEND_URL

JOB_POST_URL = lambda job_post_uid: f"{BASE_FRONTEND_URL}job-details/{job_post_uid}"

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
			encoded_value = quote_plus(str(value))  # URL encode the value
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
	def _format_working_hours(job: Job):
		"""Format working hours/available days for display in Indeed description"""
		from jobs.schemas import JobAvailableDaySchema

		available_days = job.availableday_set.all().order_by('id')
		if not available_days:
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
	def get_description(job_post: JobPost):
		context = {
		"job_title": job_post.job.get_title,
		"company_name": job_post.job.business_name(),
		"about_company": job_post.job.hiring_company_description,
		"about_job": job_post.job.about,
		"employment_type": job_post.job.employment_type.name if job_post.job.employment_type else None,
		"department": job_post.job.department.name if job_post.job.department else None,
		"job_level": job_post.job.job_level.name if job_post.job.job_level else None,
		"years_experience": f"{job_post.job.years_of_experience} Years" if job_post.job.years_of_experience else None,
		"business_model": ", ".join(job_post.job.business_models.values_list("name", flat=True)) if job_post.job.business_models.count() > 0 else None,
		"education_level": job_post.job.minimum_education_level.level if job_post.job.minimum_education_level else None,
		"qualification": job_post.job.qualification,
		"tools_platform": ", ".join(job_post.job.skills.filter(category__name="Tools/Platform").values_list("name", flat=True)) or None,
		"methodologies": ", ".join(job_post.job.skills.filter(category__name="Methodologies/Frameworks").values_list("name", flat=True)) or None,
		"general_skills": ", ".join(job_post.job.skills.filter(category__name="General Skills").values_list("name", flat=True)) or None,
		"soft_skills": ", ".join(job_post.job.skills.filter(category__name="Soft Skills").values_list("name", flat=True)) or None,
		"additional_skills": ", ".join(job_post.job.additional_skills or []) or None,
		"responsibilities": job_post.job.responsibilities,
		"payment_structure": f"{job_post.salary_type} • {job_post.salary_currency.symbol if job_post.salary_currency else '$'} {job_post.salary_min} – {job_post.salary_max}" if job_post.salary_min and job_post.salary_max else None,
		"bonus_structure": f"{job_post.salary_bonus_type} • {job_post.salary_bonus_currency.symbol if job_post.salary_bonus_currency else '$'} {job_post.salary_bonus_min} – {job_post.salary_bonus_max}" if job_post.salary_bonus_min and job_post.salary_bonus_max else None,
		"additional_benefits": ", ".join(job_post.benefits) if job_post.benefits and isinstance(job_post.benefits, list) else job_post.benefits if job_post.benefits else None,
		"break_info": f"{job_post.job.lunch_break} • {job_post.job.lunch_break_time} mins" if job_post.job.lunch_break and job_post.job.lunch_break_time else None,
		"working_hours": JobBase._format_working_hours(job_post.job),
		"tech_requirements": job_post.job.technological_requirement,
		"language": job_post.job.first_language.name if job_post.job.first_language else None,
		}
		return render_html_email("jobs/en/indeed_desc.html", context)

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
				streetaddress=job_post.get_city(),
				email=INDEED_EMAIL,
				description=JobBase.get_description(job_post),
				salary=JobBase.get_salary(job_post),
				education=JobBase.get_education(job_post),
				jobtype="".join((job.employment_type.name,)) if job.employment_type else "",
				experience=f"{job.years_of_experience} years" if job.years_of_experience else job.years_of_experience,
				lastactivitydate=job_post.last_refreshed or job_post.created_at,
				remotetype="Fully remote" if job_post.job.work_structure == WorkStructureEnum.REMOTE.value else "Hybrid remote",
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
		self.add_element(job_el, "description", self.title)
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
		if text:
			el = SubElement(parent, tag)
			el.text = escape(text)

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
				queryset=JobPost.objects.select_related("job")\
				.filter(status=JobStatusType.POSTED.value)\
				.order_by("-refresh_order"),
				pagination=pagination.Input(page=page, page_size=page_size)
			)
		else:
			queryset = JobPost.objects.select_related("job")\
				.filter(status=JobStatusType.POSTED.value)\
				.order_by("-refresh_order").iterator(chunk_size=30)

		for job_post in queryset:
			job_base = alert_bug_via_email(JobBase.convert_to_job, job_post=job_post, default=None)
			if job_base:
				xml = alert_bug_via_email(job_base.to_xml, default=None)
				if xml:
					yield tostring(xml, encoding="unicode") + "\n"
		yield '</source>\n'
