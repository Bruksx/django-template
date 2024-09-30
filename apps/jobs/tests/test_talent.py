import logging
from datetime import timezone
from decimal import Decimal

from django.test import TestCase
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from accounts.enums import BusinessUserRoleType
from accounts.models import Country, Industry, User, Talent, BusinessUser, Business, Role, EducationLevel, Department
from core.models import Currency
from jobs.enums import WorkStructureEnum, LunchBreakEnum, StageType
from jobs.models import JobPost, JobLevel, EmploymentType, Job, SavedJob, JobApplication
from jobs.views import router




class TalentJobListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.first()
        self.industry = Industry.objects.first()
        self.user_data = dict(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            password="securepassword",
        )
        self.user = User.objects.create_user(**self.user_data,
                                             email_verified=True,
                                             is_active=True)
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.role = Role.objects.first()
        self.education_level = EducationLevel.objects.first()
        self.department = Department.objects.first()
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
            location="Lekki, Lagos, Nigeria",
            industry="Technology"
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
            annual_salary_min=100000.00,
            annual_salary_max=120000.00,
            minimum_education_level=self.education_level,
            role=self.role,
            department=self.department,
            annual_salary_currency=self.currency,
            availability_timezone=timezone.utc  # Set to UTC for this example
        )
        self.job_post = JobPost.objects.create(
            job=job,
            is_posted=False,  # Can be changed to True for posting
            country=self.country,
            province="Ontario",
            postal_code="M5V 1T6",  # Replace with actual postal code
            annual_salary_min=Decimal('80000.00'),  # Use Decimal for money fields
            annual_salary_max=Decimal('100000.00'),
            annual_salary_currency=self.currency,
            location_type=WorkStructureEnum.HYBRID.value,
            recruiter=self.business_user
        )

    def test_job_recommendations_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/job-recommendations", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        response = self.client.get("talent/job-recommendations?use_filter=false&limit=100&offset=0", headers=headers)
        logging.critical(f"response: {response.content}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_saved_job_endpoints(self):
        SavedJob.objects.create(
            job_post=self.job_post,
            talent=self.talent
        )
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/saved-jobs", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        response = self.client.get("talent/saved-jobs?use_filter=false&limit=100&offset=0", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_applied_job_endpoints(self):
        JobApplication.objects.create(
            job_post=self.job_post,
            applicant=self.talent,
            is_available=True,
            accept_privacy=True,
            stage=StageType.INTERVIEW.value,
            match=5
        )
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/applied-jobs", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        response = self.client.get("talent/applied-jobs?use_filter=false&limit=100&offset=0", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

class UpdateTalentJobFilterTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email="testuser1@example.com",
                                             password="securedPassword1",
                                             first_name="Test1",
                                             last_name="User1",
                                             phone_number="9098866699")
        self.country = Country.objects.first()
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )

    def test_update_job_filter(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertFalse(hasattr(self.talent, "jobfilter"))

        data = {
          "location_type": WorkStructureEnum.IN_OFFICE.value,
          "role": "",
          "years_of_experience": 0,
          "office_location": str(Country.objects.first().uid),
          "employment_type": str(EmploymentType.objects.first().uid),
          "department": None,
          "minimum_education_level": None,
          "remove_applied_jobs": False
        }
        response = self.client.patch("talent/job-filter",
                                    json=data,
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertTrue(hasattr(self.talent, "jobfilter"))
        data["remove_applied_jobs"] = True
        data["department"] = str(Department.objects.first().uid)
        response = self.client.patch("talent/job-filter",
                                     json=data,
                                     headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.jobfilter.remove_applied_jobs, True)
        self.assertEqual(self.talent.jobfilter.department, Department.objects.first())




