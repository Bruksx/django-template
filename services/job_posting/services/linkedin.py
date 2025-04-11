from config import settings
from helpers.email.utils import render_text_email
from helpers.utils import datetime_to_epoch_milliseconds

from services.job_posting.enums.linkedIn import EmploymentStatusEnum, WorkPlaceTypeEnum, ExperienceLevelEnum
from services.job_posting.schema.linkedIn import JobSchema, CompensationSchema, CompensationsSchema, RangeValueSchema, \
	ValueSchema


def employment_type_mapper(employment_type):
	if employment_type == "Full-Time Independent Contractor":
		return EmploymentStatusEnum.FULL_TIME.value
	elif employment_type == "Part-Time Contractor":
		return EmploymentStatusEnum.PART_TIME.value
	elif employment_type == "Temporary Employee":
		return EmploymentStatusEnum.TEMPORARY.value
	elif employment_type == "Full-Time Direct Employee":
		return EmploymentStatusEnum.PERMANENT.value
	elif employment_type == "Contract Employee":
		return EmploymentStatusEnum.CONTRACT.value
	else:
		return EmploymentStatusEnum.FULL_TIME.value


def workplace_type_mapper(workplace_type):
	if not workplace_type:
		workplace_type = ""
	return dict(
		hybrid=WorkPlaceTypeEnum.HYBRID.value,
		remote=WorkPlaceTypeEnum.REMOTE.value
	).get(workplace_type.lower(), WorkPlaceTypeEnum.ONSITE.value)

def get_location(job_post):
	location = set()
	if job_post.province:
		location.add(job_post.province)
	if job_post.country:
		location.add(job_post.country.name)
	return ", ".join(location)

def get_compensation(job_post)->CompensationsSchema:
	compensation = CompensationsSchema(compensations=[])
	if job_post.annual_salary_currency and job_post.annual_salary_min and job_post.annual_salary_max:
		compensation.compensations.append(
				CompensationSchema(
					value=RangeValueSchema(
						start=ValueSchema(
							amount=str(job_post.annual_salary_min),
							currencyCode=job_post.annual_salary_currency.code
						),
						end=ValueSchema(
							amount=str(job_post.annual_salary_max),
							currencyCode=job_post.annual_salary_currency.code
						)
					),
					type="BASE_SALARY",
					period="YEARLY"
				)
		)

	if job_post.annual_bonus_currency and job_post.annual_bonus_min and job_post.annual_bonus_max:
		compensation.compensations.append(
				CompensationSchema(
					value=RangeValueSchema(
						start=ValueSchema(
							amount=str(job_post.annual_bonus_min),
							currencyCode=job_post.annual_bonus_currency.code
						),
						end=ValueSchema(
							amount=str(job_post.annual_bonus_max),
							currencyCode=job_post.annual_bonus_currency.code
						)
					),
					type="BONUS",
					period="YEARLY"
				))
		return compensation

def experience_level_mapper(experience_level):
	if not experience_level:
		experience_level = ""
	return dict(
		entry_level=ExperienceLevelEnum.ENTRY_LEVEL.value,
		junior=ExperienceLevelEnum.ENTRY_LEVEL.value,
		intermediate=ExperienceLevelEnum.MID_SENIOR_LEVEL.value,
		lead=ExperienceLevelEnum.DIRECTOR.value,
		senior=ExperienceLevelEnum.ASSOCIATE.value,
		manager=ExperienceLevelEnum.EXECUTIVE.value,
		director=ExperienceLevelEnum.DIRECTOR.value,
		vice_president=ExperienceLevelEnum.EXECUTIVE.value,
		executive_chief_officer=ExperienceLevelEnum.EXECUTIVE.value
	).get(experience_level, ExperienceLevelEnum.NOT_APPLICABLE.value)


def job_post_to_job_schema(job_post)->JobSchema:
	description = render_text_email("jobs/job_description.txt", {
		"responsibilities": job_post.job.responsibilities,
		"benefits": job_post.benefits
	})
	apply_url = f"{settings.FRONTEND_URL}/job-posts/{job_post.uid}"
	employment_status = employment_type_mapper(job_post.job.employment_type.name if job_post.job.employment_type else "")
	return JobSchema(
				title=job_post.job.title,
				description=description,
				companyApplyUrl=apply_url,
				employmentStatus=employment_status,
				externalJobPostingId=str(job_post.uid),
				listedAt=datetime_to_epoch_milliseconds(job_post.created_at),
				location=get_location(job_post),
				workplaceTypes=workplace_type_mapper(job_post.job.work_structure),
				compensation=get_compensation(job_post),
				experienceLevel=experience_level_mapper(job_post.job.job_level.name if job_post.job.job_level else ""),
			)
