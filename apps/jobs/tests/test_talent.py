import uuid
from datetime import timezone
from decimal import Decimal

from accounts.enums import BusinessUserRoleType
from accounts.models import Country, Industry, User, Talent, BusinessUser, Business, Role, EducationLevel, Department
from core.models import Currency
from django.test import TestCase

from factories import TalentFactory, JobPostFactory, BusinessUserFactory
from jobs.enums import WorkStructureEnum, LunchBreakEnum, StageType, JobStatusType
from jobs.models import JobPost, JobLevel, EmploymentType, Job, SavedJob, JobApplication, JobFilter
from jobs.views import router
from ninja.testing import TestClient


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
            status=JobStatusType.CLOSED.value,  # Can be changed to True for posting
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
        response = self.client.get("talent/job-recommendations?use_filter=false&page_size=100&page=1", headers=headers)
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
        response = self.client.get("talent/saved-jobs?use_filter=false&page_size=100&page=1", headers=headers)
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
        response = self.client.get("talent/applied-jobs?use_filter=false&page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_job_post_list_endpoints(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/job-posts", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        # when talent has no job filter
        response = self.client.get("talent/job-posts?use_filter=true&page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 400)

        response = self.client.get("talent/job-posts?search=test", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

        # when talent now has a job filter
        JobFilter.objects.create(
            talent=self.talent,
        )
        response = self.client.get("talent/job-posts?use_filter=true&page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)


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

class GetTalentJobFilterTest(TestCase):
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

    def test_get_job_filter_endpoint_without_job_filter(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/job-filter", headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_get_job_filter_endpoint_with_job_filter(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        JobFilter.objects.create(
            talent=self.talent,
        )
        response = self.client.get("talent/job-filter", headers=headers)
        self.assertEqual(response.status_code, 200)

class ApplyToJobPostTest(TestCase):
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
        self.job = Job.objects.create(
            title="Test Job"
        )
        self.job_post = JobPost.objects.create(
            job=self.job,)

    def test_apply_to_job_post(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        job_post_id = str(JobPost.objects.first().uid)
        data = {
         "accept_privacy": True,
         "is_available": True,
        }
        self.assertEqual(self.talent.applied_jobs().count(), 0)
        response = self.client.post(f"talent/job-posts/{job_post_id}/apply",
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        # test to ensure that you cannot apply for one job twice
        response = self.client.post(f"talent/job-posts/{job_post_id}/apply",
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 400)

class WithdrawJobApplicationTest(TestCase):
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
        self.job = Job.objects.create(
            title="Test Job"
        )
        self.job_post = JobPost.objects.create(
            job=self.job,)

        self.job_application = JobApplication.objects.create(
            job_post=self.job_post,
            applicant=self.talent,
            is_available=True,
            accept_privacy=True,
            stage=None,
            match=5
        )

    def test_withdraw_job_application(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        job_application_id = str(JobApplication.objects.first().uid)
        data = {
            "feedback": "Test Feedback"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        response = self.client.post(f"talent/job-posts/applications/{job_application_id}/withdraw",
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 0)

    def test_withdraw_for_job_application_with_stage(self):
        self.job_application.stage = StageType.INTERVIEW.value
        self.job_application.save()
        self.job_application.refresh_from_db()
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        job_application_id = str(JobApplication.objects.first().uid)
        data = {
            "feedback": "Test Feedback"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        response = self.client.post(f"talent/job-posts/applications/{job_application_id}/withdraw",
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 400)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)


class ShareJobPostViaEmailTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email="testuser1@example.com",
                                             password="securedPassword1",
                                             first_name="Test1",
                                             last_name="User1",
                                             phone_number="9098866699")
        self.user2 = User.objects.create_user(email="testuser2@example.com",
                                             password="securedPassword1",
                                             first_name="Test2",
                                             last_name="User2",
                                             phone_number="9098866699")
        self.talent2 = Talent.objects.create(user=self.user2)

        self.country = Country.objects.first()
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.job = Job.objects.create(
            title="Test Job"
        )
        self.job_post = JobPost.objects.create(
            job=self.job,)

    def test_share_job_post_via_email(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        job_post_id = str(JobPost.objects.first().uid)
        data = {
         "talents": [str(self.talent2.user.uid)],
         "emails": ["testuser3@example.com", "testuser4@example.com"]
        }
        response = self.client.post(f"talent/job-posts/{job_post_id}/share-via-email",
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 200)

class SaveJobTest(TestCase):
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
        self.job = Job.objects.create(
            title="Test Job"
        )
        self.job_post = JobPost.objects.create(
            job=self.job,)

    def test_save_job(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertEqual(self.talent.saved_jobs().count(), 0)
        job_post_id = str(JobPost.objects.first().uid)
        response = self.client.post(f"talent/job-posts/{job_post_id}/save",
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.saved_jobs().count(), 1)
        # test to ensure that you cannot save for one job twice
        response = self.client.post(f"talent/job-posts/{job_post_id}/save",
                                    headers=headers)
        self.assertEqual(response.status_code, 400)

class DiscardSavedJobTest(TestCase):
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
        self.job = Job.objects.create(
            title="Test Job"
        )
        self.job_post = JobPost.objects.create(
            job=self.job,)

    def test_discard_saved_job_endpoint_without_job_post_saved(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertEqual(self.talent.saved_jobs().count(), 0)
        job_post_id = str(JobPost.objects.first().uid)
        response = self.client.post(f"talent/job-posts/{job_post_id}/discard",
                                    headers=headers)
        self.assertEqual(response.status_code, 404)
        self.talent.refresh_from_db()

    def test_discard_saved_job_endpoint_with_job_post_saved(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        SavedJob.objects.create(
            job_post=self.job_post,
            talent=self.talent
        )
        self.assertEqual(self.talent.saved_jobs().count(), 1)
        job_post_id = str(JobPost.objects.first().uid)
        response = self.client.post(f"talent/job-posts/{job_post_id}/discard",
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.saved_jobs().count(), 0)

class TestShareJobViaChat(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.talent = TalentFactory.create()
        TalentFactory.create_batch(3)
        self.job_post = JobPostFactory.create()

    def test_share_job_post_via_chat(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talent_ids" : list(Talent.objects.only("uid").exclude(uid=self.talent.uid).values_list("uid", flat=True))
        }
        response = self.client.post(f"talent/job-posts/{self.job_post.uid}/share-via-chat", headers=header, json=data)
        self.assertEqual(response.status_code, 200)

    def test_request_by_business_user(self):
        business_user = BusinessUserFactory.create()
        header = {
            "Authorization": f"Bearer {business_user.user.token}"
        }
        data = {
            "talent_ids" : list(Talent.objects.only("uid").exclude(uid=self.talent.uid).values_list("uid", flat=True))
        }
        response = self.client.post(f"talent/job-posts/{self.job_post.uid}/share-via-chat", headers=header, json=data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Only Talents are allowed")

    def test_wrong_job_post_id(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talent_ids" : list(Talent.objects.only("uid").exclude(uid=self.talent.uid).values_list("uid", flat=True))
        }
        response = self.client.post(f"talent/job-posts/{uuid.uuid4()}/share-via-chat", headers=header, json=data)
        self.assertEqual(response.status_code, 404)

    def test_empty_talent_ids(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talent_ids" : []
        }
        response = self.client.post(f"talent/job-posts/{self.job_post.uid}/share-via-chat", headers=header, json=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "No talents selected")

    def test_wrong_talent_ids_data(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talent_ids" : [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        }
        response = self.client.post(f"talent/job-posts/{self.job_post.uid}/share-via-chat", headers=header, json=data)
        self.assertEqual(response.status_code, 200)