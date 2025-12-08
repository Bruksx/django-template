from concurrent.futures import ThreadPoolExecutor

import pytz
import requests
from accounts.enums import BusinessSize, BusinessUserRoleType
from accounts.models import BusinessUser, Department, Role, Country, Business, User
from core.models import Currency
from django.db import transaction
from django.db.transaction import atomic
from jobs.enums import JobStatusType, LunchBreakEnum, WorkStructureEnum, PhaseType
from jobs.models import Job, JobPost, EmploymentType, JobLevel
from settings.models import WorkFlowStage
from django.db import connection, close_old_connections

from apps.accounts.enums import UserType
from apps.core.models import State, City
from config import settings
from helpers.utils import chunk_queryset


def handle_job_work_place(work_type):
    choices = {
        "remote": WorkStructureEnum.REMOTE,
        "hybrid": WorkStructureEnum.HYBRID,
        "onsite": WorkStructureEnum.IN_OFFICE
    }
    return choices.get(work_type, WorkStructureEnum.REMOTE)


def create_job(job_data):
    with atomic():
        business_user = BusinessUser.objects.filter(user__email__iexact=settings.EIGHTEEN_FORTY_EMAIL).first()
        if not business_user:
            return
        country = Country.objects.filter(code__iexact=job_data.get("country")).first()
        department = Department.objects.filter(name__icontains=job_data.get("categories", {}).get("team", "")).first()
        role = Role.objects.filter(name__icontains=job_data.get("text", "")).first()
        currency = Currency.objects.filter(abbreviation=job_data.get("salaryRange", {}).get("currency", "USD")).first()
        employment_type = EmploymentType.objects.filter(
            name__icontains=job_data.get("categories", {}).get("commitment", "")).first()
        job_level = JobLevel.objects.filter(name__icontains=job_data.get("categories", {}).get("department", "")).first()

        responsibilities = [
            item.strip() for block in job_data.get("lists", [])
            if block["text"].lower().startswith("responsibilities")
            for item in block["content"].replace("<li>", "").replace("</li>", "").split("\n") if item.strip()
        ]

        qualification = "\n".join([
            item.strip() for block in job_data.get("lists", [])
            if block["text"].lower().startswith("requirements")
            for item in block["content"].replace("<li>", "").replace("</li>", "").split("\n") if item.strip()
        ])

        preferred_skills = "\n".join([
            item.strip() for block in job_data.get("lists", [])
            if block["text"].lower().startswith("preferred")
            for item in block["content"].replace("<li>", "").replace("</li>", "").split("\n") if item.strip()
        ])

        job_title = job_data.get("text", "")

        province_ = job_data.get("categories", {}).get("location", "").split(",")[1].strip() if "," in job_data.get(
            "categories", {}).get("location", "") else ""
        province = State.objects.filter(name__icontains=province_).first()
        city_ = job_data.get("categories", {}).get("location", "").split(",")[0].strip()
        city = City.objects.filter(name__icontains=city_).first()
        timez = [tz for tz in pytz.all_timezones if city_.lower() in tz.lower() or province_.lower() in tz.lower()]
        timez = timez[0] if timez else None

        job, _ = Job.objects.update_or_create(
            title=job_title,
            defaults={
                "hiring_company_name": "1840 & Company",
                "hiring_company_description": job_data.get("additionalPlain"),
                "about": job_data.get("descriptionPlain"),
                "employment_type": employment_type,
                "department": department,
                "role": role,
                "job_level": job_level,
                "created_by": business_user,
                "qualification": qualification,
                "additional_skills": preferred_skills,
                "responsibilities": responsibilities,
                "work_structure": handle_job_work_place(job_data.get("workplaceType")),
                "office_address": job_data.get("categories", {}).get("location", "Remote"),
                "lunch_break": LunchBreakEnum.UNPAID,
                "availability_timezone": timez,
            }
        )

        j, _ = JobPost.objects.update_or_create(
            job=job,
            defaults={
                "status": JobStatusType.DRAFT.value,
                "country": country,
                "posted_by": business_user,
                "recruiter": business_user,
                "province": province,
                "city": city.name,
                "salary_min": job_data.get("salaryRange", {}).get("min"),
                "salary_max": job_data.get("salaryRange", {}).get("max"),
                "salary_currency": currency,
                "share_compensation": False,
            }
        )

def import_lever_jobs():
    with transaction.atomic():
        company_name = "1840 & Company"
        eighteen_forty_email = settings.EIGHTEEN_FORTY_EMAIL
        eighteen_forty_password = settings.EIGHTEEN_FORTY_PASSWORD

        # create business and business user

        if not company_name or not eighteen_forty_email or not eighteen_forty_password:
            raise Exception("Missing company name, email or password")

        business = Business.objects.filter(name__iexact=company_name).first()
        if not business:
            business = Business.objects.create(
                name=company_name,
                size=BusinessSize.SIZE_51_250,
                website="https://www.1840andco.com/",
                country=Country.objects.filter(name__iexact="United States").first(),
                address="5440 W. 110th St Building 2, Suite 300 Overland Park, KS 66211"
            )
        user = User.objects.filter(email__iexact=eighteen_forty_email).first()
        if not user:
            user = User.objects.create_user(
                email=eighteen_forty_email,
                password=eighteen_forty_password,
                first_name="1840",
                last_name="Co",
                email_verified=True,
                is_active=True,
                type=UserType.BUSINESS,
            )

        if not BusinessUser.objects.filter(business=business, user=user).exists():
            BusinessUser.objects.create(business=business, user=user, role=BusinessUserRoleType.OWNER.value)
        business.update(created_by=user)

        # fetch job
        url = f"https://api.lever.co/v0/postings/1840%26Company?mode=json"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch Lever jobs. Status: {response.status_code}")

        #check for workflow stages
        for phase in PhaseType.values():
            if not WorkFlowStage.objects.filter(phase=phase, created_by__business=business).exists():
                raise Exception(f"Workflow stage for phase {phase} does not exist")

        jobs_data = response.json()
        with ThreadPoolExecutor(max_workers=20) as executor:
            for chunk in chunk_queryset(jobs_data):
                executor.map(create_job, chunk)
        connection.close()
        close_old_connections()
