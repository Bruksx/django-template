from datetime import timezone
from decimal import Decimal

from django.test import TestCase
from ninja_jwt.authentication import JWTAuth

from accounts.enums import BusinessUserRoleType
from accounts.models import (
    Country, Industry, User, Talent, BusinessUser, Business, Department, Role, EducationLevel, BusinessIndustry
)
from core.models import Currency
from jobs.enums import LunchBreakEnum, WorkStructureEnum, JobStatusType
from jobs.models import JobPost, Job, JobLevel, EmploymentType, JobFilter, JobApplication


class JobFilterModelTest(TestCase):
    def setUp(self):
        self.country = Country.objects.first()
        self.industry = Industry.objects.first()
        self.business_industry = BusinessIndustry.objects.first()
        self.user_data = dict(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            password="securepassword",
        )
        self.user = User.objects.create_user(**self.user_data)
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.auth = JWTAuth()
        self.auth.authenticate = lambda r: self.user
        self.role = Role.objects.first()
        self.education_level=EducationLevel.objects.first()
        self.department=Department.objects.first()
        self.currency = Currency.objects.first()
        self.job_level = JobLevel.objects.first()
        self.employment_type = EmploymentType.objects.first()
        self.country = Country.objects.first()
        self.user2 = User.objects.create_user(
            email="testuser1@example.com",
            password="securedPassword1",
            first_name="Test1",
            last_name="User1",
            phone_number="9098866699"
        )
        self.business = Business.objects.create(
            created_by=self.user2,
            name="Example Business",
            size=50,
            description="A sample business description.",
            website="https://example.com",
            address="Lekki, Lagos, Nigeria",
            country=Country.objects.first().uid,
            industry=self.business_industry,
        )
        self.business_user = BusinessUser.objects.create(
            user=self.user,
            business=self.business,
            role=BusinessUserRoleType.OWNER.value

        )

        job = Job.objects.create(
            created_by=self.business_user,
            job_level=self.job_level,
            employment_type=self.employment_type,
            hiring_company_name="Example Company",
            title="Software Engineer",
            about="We are looking for a passionate...",  # Truncated for brevity
            years_of_experience=3,
            lunch_break=LunchBreakEnum.PAID.value,  # Assuming LunchBreakEnum has a PAID option
            minimum_education_level=self.education_level,
            role=self.role,
            department=self.department,
            availability_timezone=timezone.utc  # Set to UTC for this example
        )
        self.job_post = JobPost.objects.create(
            job=job,
            status=JobStatusType.CLOSED.value,  # Can be changed to True for posting
            country=self.country,
            province="Ontario",
            postal_code="M5V 1T6",  # Replace with actual postal code
            annual_salary_min=Decimal('80000.00'),  # Use Decimal for money fields
            annual_salary_max=Decimal('100000.00'),
            annual_salary_currency=self.currency,
            recruiter=self.business_user
        )


    def test_get_queryset(self):
        queryset = JobPost.objects.all()
        JobFilter.objects.create(
            talent = self.talent,
            role="",
            years_of_experience=2,
            office_location=self.country,
            employment_type=self.employment_type,
            department=self.department,
            minimum_education_level=self.education_level,
            location_type=WorkStructureEnum.HYBRID,
            remove_applied_jobs=False

        )
        filtered_queryset = self.talent.jobfilter.get_queryset(queryset)

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(filtered_queryset.count(), 0)

        self.talent.jobfilter.update(remove_applied_jobs=True)
        JobApplication.objects.create(
            applicant=self.talent,
            job_post=self.job_post,
            match=5
        )
        filtered_queryset = self.talent.jobfilter.get_queryset(queryset)
        self.assertEqual(filtered_queryset.count(), 0)



