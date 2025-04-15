import uuid
from datetime import timezone
from decimal import Decimal

from django.test import TestCase
from ninja.testing import TestClient

from accounts.enums import BusinessUserRoleType
from accounts.models import (
    Country, Industry, User, Talent, BusinessUser, Business, Role, EducationLevel, Department, BusinessIndustry
)
from core.models import Currency
from factories import TalentFactory, JobPostFactory, BusinessUserFactory, JobFactory, WorkflowStageFactory, \
    JobApplicationFactory, CountryFactory, ScreeningQuestionFactory, fake
from jobs.enums import WorkStructureEnum, LunchBreakEnum, PhaseType, JobStatusType, WithdrawalFeedbackType, \
    QuestionTypeEnum
from jobs.models import JobPost, JobLevel, EmploymentType, SavedJob, JobApplication, JobFilter
from jobs.views import router


class TalentJobListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.first()
        self.industry = Industry.objects.first()
        self.business_industry = BusinessIndustry.objects.first()
        self.user_data = dict(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            password="securepassword",
        )
        self.user = User.objects.create_user(**self.user_data,
                                             email_verified=True,
                                             is_active=True)
        self.talent = TalentFactory.create(user=self.user, country=self.country)
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
            address="Lekki, Lagos, Nigeria",
            country=Country.objects.first().uid,
            industry=self.business_industry,
        )
        self.business_user = BusinessUser.objects.create(
            user=self.user,
            business=self.business,
            role=BusinessUserRoleType.OWNER.value
        )

        job = JobFactory.create(
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
        job.requiredattribute.update(
            role=True,
            job_level=True,
            years_of_experience=True,
            minimum_education_level=True,
            work_structure=True,
            technological_requirement=True,
            first_language=True,
            secondary_language=True,
            working_hours=True,
            location=True
        )
        self.job_post = JobPostFactory.create(
            job=job,
            status=JobStatusType.POSTED.value,  # Can be changed to True for posting
            country=self.country,
            province="Ontario",
            postal_code="M5V 1T6",  # Replace with actual postal code
            annual_salary_min=Decimal('80000.00'),  # Use Decimal for money fields
            annual_salary_max=Decimal('100000.00'),
            annual_salary_currency=self.currency,
            recruiter=self.business_user
        )

    def test_job_recommendations_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/job-recommendations", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        response = self.client.get("talent/job-recommendations?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_job_recommendations_endpoint_without_availability(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.talent.talentavailableday_set.all().delete()
        response = self.client.get("talent/job-recommendations", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        response = self.client.get("talent/job-recommendations?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

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
        response = self.client.get("talent/saved-jobs?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_applied_job_endpoints(self):
        stage = WorkflowStageFactory.create(phase=PhaseType.INTERVIEW.value)
        application = JobApplication.objects.create(
            job_post=self.job_post,
            applicant=self.talent,
            stage=stage,
            match=5
        )
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/applied-jobs", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["application_uid"], str(application.uid))
        self.assertEqual(response.json()["results"][0]["stage"]["uid"], str(stage.uid))

        response = self.client.get("talent/applied-jobs?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)


    def test_job_post_list_endpoints(self):

        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("talent/job-posts?sort_by=date-posted&page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertIn("weakness", response.json()["results"][0])
        self.assertIn("strength", response.json()["results"][0])
        self.assertIn("non_negotiable", response.json()["results"][0])
        strength = response.json()["results"][0]["strength"]
        self.assertIn("match_score", strength)
        self.assertGreaterEqual(strength["match_score"], 0)

        # when talent has no job filter
        response = self.client.get("talent/job-posts?page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get("talent/job-posts?search=test&page_size=100&page=1", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

        # when talent now has a job filter
        JobFilter.objects.create(
            talent=self.talent,
        )
        response = self.client.get("talent/job-posts?page_size=100&page=1&sort_by=date-posted", headers=headers)
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
          "job_level": str(JobLevel.objects.first().uid),
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
        self.assertEqual(response.status_code, 200)

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
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.business_user = self.job.created_by
        self.job_post = JobPostFactory.create(
            status=JobStatusType.POSTED.value,
            job=self.job,)
        self.test_data = {
            "available_for_schedule": True
        }
        self.url = lambda job_post_uid: f"talent/job-posts/{job_post_uid}/apply"
        WorkflowStageFactory.create(phase=PhaseType.REJECTED.value, created_by=self.job.created_by)

    def test_apply_to_job_post_without_screening_answers(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 0)
        response = self.client.post(self.url(self.job_post.uid), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)

        # test to ensure that you cannot apply for one job twice
        response = self.client.post(self.url(self.job_post.uid), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_apply_to_job_post_with_screening_answers(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        questions = ScreeningQuestionFactory.create_batch(5, job=self.job)
        data = list()
        for question in questions:
            answer_dict = dict(question=question.uid)
            if question.type == QuestionTypeEnum.SINGLE_SELECT.value:
                answer_dict["options"] = [question.questionoption_set.first().uid]
            elif question.type == QuestionTypeEnum.MULTI_SELECT.value:
                answer_dict["options"] = [option.uid for option in question.questionoption_set.all()[:2]]
            elif question.type == QuestionTypeEnum.TEXT.value:
                answer_dict["text"] = fake.text(max_nb_chars=20)
            elif question.type == QuestionTypeEnum.FILE.value:
                answer_dict["files"] = ["http://test.com"]
            data.append(answer_dict)
        self.test_data["answers"] = data
        response = self.client.post(self.url(self.job_post.uid),
                                    headers=headers, json=self.test_data)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        application = self.talent.jobapplication_set.first()
        self.assertEqual(application.answer_set.count(), 5)

    def test_by_business_user(self):

        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.job_post.uid), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_with_invalid_job_post_uid(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.post(self.url(uuid.uuid4()), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 404)


    def test_low_application_score(self):
        match_score = self.talent.job_match_score(self.job_post)
        self.job.update(min_match_score=(match_score + 1))
        self.job.refresh_from_db()
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 0)
        response = self.client.post(self.url(self.job_post.uid), json=self.test_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        application = self.talent.jobapplication_set.first()
        self.assertEqual(application.stage.phase, PhaseType.REJECTED.value)



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
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.job_post = JobPostFactory.create(
            job=self.job,
            status=JobStatusType.POSTED.value
        )

        self.job_application = JobApplication.objects.create(
            job_post=self.job_post,
            applicant=self.talent,
            stage=None,
            match=5
        )

    def test_withdraw_job_application(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        job_application_id = str(JobApplication.objects.first().uid)
        data = {
            "feedback_type": WithdrawalFeedbackType.SKILLS.value,
            "feedback": "Test Feedback"
        }
        self.assertEqual(self.talent.applied_jobs().count(), 1)
        response = self.client.post(f"talent/job-posts/applications/{job_application_id}/withdraw",
                                    headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.applied_jobs().count(), 0)

    def test_withdraw_for_job_application_with_stage(self):
        stage = WorkflowStageFactory.create(phase=PhaseType.INTERVIEW.value)
        self.job_application.stage = stage
        self.job_application.save()
        self.job_application.refresh_from_db()
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        job_application_id = str(JobApplication.objects.first().uid)
        data = {
            "feedback_type": WithdrawalFeedbackType.SKILLS.value,
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
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.job_post = JobPostFactory.create(
            job=self.job,)

        self.url = f"share/via-email"

    def test_share_job_post_via_email(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
         "emails": ["testuser3@example.com", "testuser4@example.com"],
         "jobs": [str(self.job.uid)]
        }
        response = self.client.post(self.url,
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
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.job_post = JobPostFactory.create(
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
        self.job = JobFactory.create(
            title="Test Job"
        )
        self.job_post = JobPostFactory.create(
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
        TalentFactory.create_batch(3, country=self.talent.country)
        self.job_post = JobPostFactory.create(country=self.talent.country)
        self.url = f"share/via-chat"

    def test_share_job_post_via_chat(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talents" : list(Talent.objects.only("uid").exclude(uid=self.talent.uid).values_list("uid", flat=True)),
            "jobs": [self.job_post.job.uid]
        }
        self.assertEqual(self.job_post.message_set.count(), 0)
        response = self.client.post(self.url, headers=header, json=data)
        self.job_post.refresh_from_db()
        self.assertEqual(self.job_post.message_set.count(), 3)
        self.assertEqual(response.status_code, 200)

    def test_request_by_business_user(self):
        business_user = BusinessUserFactory.create()
        header = {
            "Authorization": f"Bearer {business_user.user.token}"
        }
        data = {
            "talents" : list(Talent.objects.only("uid").exclude(uid=self.talent.uid).values_list("uid", flat=True)),
            "jobs": [self.job_post.job.uid]
        }
        response = self.client.post(self.url, headers=header, json=data)
        self.assertEqual(response.status_code, 200)


    def test_empty_talent_ids(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talents" : [],
            "jobs": [self.job_post.job.uid]
        }
        response = self.client.post(self.url, headers=header, json=data)
        self.assertEqual(response.status_code, 400)

    def test_wrong_talent_ids_data(self):
        header = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        data = {
            "talents" : [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()],
            "jobs": [self.job_post.job.uid]
        }
        response = self.client.post(self.url, headers=header, json=data)
        self.assertEqual(response.status_code, 200)

class TestJobRecommendationsEndpoint(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = lambda talent_uid: f"talents/{talent_uid}/job-recommendations"
        self.business_user = BusinessUserFactory.create()
        self.business = self.business_user.business
        country = CountryFactory.create()
        years_of_experience = 3
        self.talent = TalentFactory.create(years_of_experience=years_of_experience, country=country)
        jobs = JobFactory.create_batch(5, created_by=self.business_user, years_of_experience=years_of_experience)
        for job in jobs:
            job.requiredattribute.update(job=job, years_of_experience=True, location=True)
            JobPostFactory.create(job=job, posted_by=self.business_user, country=country)
        JobApplicationFactory.create(job_post=JobPost.objects.first(), applicant=self.talent)

    def test_job_recommendations_endpoint(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.talent.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 5)


    def test_endpoint_by_talent(self):
        headers = {
            "authorization": f"Bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url(self.talent.uid), headers=headers)
        self.assertEqual(response.status_code, 403)


    def test_endpoint_with_invalid_talent_uid(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid.uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)
