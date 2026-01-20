from apps.jobs.models import JobPost
from config import settings
from helpers.utils import datetime_to_epoch_milliseconds, html_to_text

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
        location.add(job_post.province.name if job_post.province else "")
    if job_post.country:
        location.add(job_post.country.name if job_post.country else "")
    return ", ".join(location)

def get_linkedin_period(period):
    return {
        "Hourly": "HOURLY",
        "Daily": "DAILY",
        "Weekly": "WEEKLY",
        "Bi-Weekly": "BIWEEKLY",
        "Monthly": "MONTHLY",
        "Bi-Monthly": "SEMIMONTHLY",
        "Annually": "YEARLY"
    }.get(period, "ONCE")

def get_compensation(job_post)->CompensationsSchema:
    compensation = CompensationsSchema(compensations=[])
    if job_post.salary_currency and job_post.salary_min and job_post.salary_max:
        compensation.compensations.append(
                CompensationSchema(
                    value=RangeValueSchema(
                        start=ValueSchema(
                            amount=str(job_post.salary_min),
                            currencyCode=job_post.salary_currency.abbreviation
                        ),
                        end=ValueSchema(
                            amount=str(job_post.salary_max),
                            currencyCode=job_post.salary_currency.abbreviation
                        )
                    ),
                    type="BASE_SALARY",
                    period=get_linkedin_period(job_post.salary_type)
                )
        )

    if job_post.salary_bonus_currency and job_post.salary_bonus_min and job_post.salary_bonus_max:
        compensation.compensations.append(
                CompensationSchema(
                    value=RangeValueSchema(
                        start=ValueSchema(
                            amount=str(job_post.salary_bonus_min),
                            currencyCode=job_post.salary_bonus_currency.abbreviation
                        ),
                        end=ValueSchema(
                            amount=str(job_post.salary_bonus_max),
                            currencyCode=job_post.salary_bonus_currency.abbreviation
                        )
                    ),
                    type="BONUS",
                    period=get_linkedin_period(job_post.salary_bonus_type)
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


def get_description(job_post:JobPost, job) -> str:
    parts = []
    # handle promotional tag
    promotion_tag = job_post.linkedin_tags[0] if job_post.linkedin_tags else None
    if promotion_tag:
        parts.append(f"{promotion_tag} \n\n")
        
    # About Job
    if job_post.get_about():
        about = job_post.get_about()
        parts.append("About the Job\n")
        parts.append(f"{about.strip()}\n\n\n")

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
        parts.append("Job Details\n")
        for d in details:
            parts.append(f"  • {d}\n")
        parts.append("\n\n")

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
        parts.append("Required Skills\n")
        for s in skills_lines:
            parts.append(f"  • {s}\n")
        parts.append("\n\n")

    # Responsibilities
    if job.responsibilities:
        parts.append("Responsibilities\n")
        parts.append(html_to_text(job.responsibilities))
        parts.append("\n\n")

    # Salary & Benefits
    salary_parts = []
    if job_post.salary_min and job_post.salary_max:
        cur = job_post.salary_currency.symbol if job_post.salary_currency else "$"
        salary_parts.append(f"Pay: {job_post.salary_type}, {cur} {job_post.salary_min} – {job_post.salary_max}")
    if job_post.salary_bonus_min and job_post.salary_bonus_max:
        cur = job_post.salary_bonus_currency.symbol if job_post.salary_bonus_currency else "$"
        salary_parts.append(
            f"Bonus: {job_post.salary_bonus_type}, {cur} {job_post.salary_bonus_min} – {job_post.salary_bonus_max}")
    if job_post.benefits:
        benefits = ", ".join(job_post.benefits) if isinstance(job_post.benefits, list) else job_post.benefits
        salary_parts.append(f"Benefits: {benefits}")
    if job.lunch_break and job.lunch_break_time:
        salary_parts.append(f"Break: {str(job.lunch_break).title()}, {job.lunch_break_time} mins")

    if salary_parts:
        parts.append("Salary & Benefits\n")
        for s in salary_parts:
            parts.append(f"  • {s}\n")
        parts.append("\n\n")

    # Working Hours
    if hasattr(job, 'availableday_set') and job.availableday_set.exists():
        parts.append("Working Hours\n")
        for day in job.availableday_set.all().order_by('id'):
            if day.start_time and day.end_time:
                parts.append(
                    f"  - {day.day}: {day.start_time.strftime('%H:%M')} - {day.end_time.strftime('%H:%M')}\n")
            else:
                parts.append(f"  - {day.day}: Available\n")
        parts.append("\n\n")

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
        parts.append("Additional Requirements\n")
        for e in extra:
            parts.append(f"  • {e}\n")
        parts.append("\n\n")

    # About Company
    if job.hiring_company_description:
        parts.append("About the Company\n")
        parts.append(f"{job.hiring_company_description.strip()}\n\n\n")

    return "".join(parts)

def job_post_to_job_schema(job_post, lang="en")->JobSchema:
    description = get_description(job_post, job_post.job)
    apply_url = f"{settings.FRONTEND_URL}jobs-listing/{job_post.uid}"
    employment_status = employment_type_mapper(job_post.job.employment_type.name if job_post.job.employment_type else "")
    return JobSchema(
                title=job_post.job.get_title,
                description=description,
                companyApplyUrl=apply_url,
                company=job_post.job.get_company(),
                employmentStatus=employment_status,
                externalJobPostingId=str(job_post.uid),
                listedAt=datetime_to_epoch_milliseconds(job_post.date_posted or job_post.created_at),
                location=get_location(job_post),
                workplaceTypes=[workplace_type_mapper(job_post.job.work_structure)],
                compensation=get_compensation(job_post),
                experienceLevel=experience_level_mapper(job_post.job.job_level.name if job_post.job.job_level else ""),
            )
