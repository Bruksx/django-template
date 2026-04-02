import uuid
from datetime import time
from decimal import Decimal, ROUND_HALF_UP
from random import choice
from uuid import uuid4

from accounts.enums import Days
from accounts.models import Department, Role, Business, Industry, BusinessUser, Skill, User, Country, Talent, \
    EducationLevel, SkillCategory, Experience, TalentAvailableDay
from core.models import City, State
from core.models import Currency
from django.db import models
from django.test import TestCase
from django.utils import timezone
from factories import BusinessFactory, BusinessUserFactory, TalentFactory, JobPostFactory, RequiredAttributeFactory, \
    JobFactory, JobApplicationFactory, WorkflowStageFactory, UserFactory, CountryFactory, ScreeningQuestionFactory, \
    AnswerFactory, CurrencyFactory, ExperienceFactory
from future.backports.datetime import timedelta
from jobs.business_views import router
from jobs.enums import JobStatusType, PhaseType, QuestionTypeEnum, ActionType
from jobs.models import (
    Job, AvailableDay, JobPost, ScreeningQuestion, QuestionOption, Language, EmploymentType, JobLevel, JobApplication,
    BusinessModel, RequiredSkill, RequiredAttribute, RequiredSecondaryLanguage, JobPostTag
)
from jobs.queries import add_application_match_score
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth
from settings.models import WorkFlowStage


class GetOtherApplicationsTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(business=self.business)
        self.other_business = BusinessFactory.create()
        self.other_business_user = BusinessUserFactory.create(business=self.other_business)
        
        # Create talent
        self.talent = TalentFactory.create()
        
        # Create jobs and job posts for the business
        self.job1 = JobFactory.create(created_by=self.business_user)
        self.job2 = JobFactory.create(created_by=self.business_user)
        self.job3 = JobFactory.create(created_by=self.other_business_user)  # Different business
        
        self.job_post1 = JobPostFactory.create(job=self.job1)
        self.job_post2 = JobPostFactory.create(job=self.job2)
        self.job_post3 = JobPostFactory.create(job=self.job3)
        
        # Create applications by the same talent
        self.application1 = JobApplicationFactory.create(
            job_post=self.job_post1,
            applicant=self.talent,
            recruiter=self.business_user
        )
        self.application2 = JobApplicationFactory.create(
            job_post=self.job_post2,
            applicant=self.talent,
            recruiter=self.business_user
        )
        self.application3 = JobApplicationFactory.create(
            job_post=self.job_post3,
            applicant=self.talent,
            recruiter=self.other_business_user
        )
        
        # Create another talent with applications
        self.other_talent = TalentFactory.create()
        self.other_application = JobApplicationFactory.create(
            job_post=self.job_post1,
            applicant=self.other_talent,
            recruiter=self.business_user
        )
        
        self.url = lambda application_uid: f"applications/{application_uid}/other-applications"

    def test_get_other_applications_success(self):
        """Test getting other applications by the same talent for the same business"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.application1.uid), headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return the other application by the same talent for the same business
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['uid'], str(self.application2.uid))

    def test_get_other_applications_no_other_applications(self):
        """Test when talent has no other applications for the same business"""
        # Create a new talent with only one application
        single_talent = TalentFactory.create()
        single_application = JobApplicationFactory.create(
            job_post=self.job_post1,
            applicant=single_talent,
            recruiter=self.business_user
        )
        
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(single_application.uid), headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 0)

    def test_get_other_applications_unauthorized(self):
        """Test that unauthorized users cannot access the endpoint"""
        response = self.client.get(self.url(self.application1.uid))
        
        self.assertEqual(response.status_code, 401)

    def test_get_other_applications_non_business_user(self):
        """Test that non-business users cannot access the endpoint"""
        headers = {
            "authorization": f"Bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url(self.application1.uid), headers=headers)
        
        self.assertEqual(response.status_code, 403)

    def test_get_other_applications_application_not_found(self):
        """Test when application UID doesn't exist"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid4()), headers=headers)
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("This application does not exist", response.json()['detail'])

    def test_get_other_applications_different_business_access_denied(self):
        """Test that business users cannot access applications from other businesses"""
        headers = {
            "authorization": f"Bearer {self.other_business_user.user.token}"
        }
        response = self.client.get(self.url(self.application1.uid), headers=headers)
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("This application does not exist", response.json()['detail'])

    def test_get_other_applications_multiple_other_applications(self):
        """Test when talent has multiple other applications for the same business"""
        # Create additional job posts and applications
        job4 = JobFactory.create(created_by=self.business_user)
        job5 = JobFactory.create(created_by=self.business_user)
        job_post4 = JobPostFactory.create(job=job4)
        job_post5 = JobPostFactory.create(job=job5)
        
        application3 = JobApplicationFactory.create(
            job_post=self.job_post2,
            applicant=self.talent,
            recruiter=self.business_user
        )
        application4 = JobApplicationFactory.create(
            job_post=job_post4,
            applicant=self.talent,
            recruiter=self.business_user
        )
        application5 = JobApplicationFactory.create(
            job_post=job_post5,
            applicant=self.talent,
            recruiter=self.business_user
        )
        
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(application3.uid), headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return other applications by the same talent for the same business
        self.assertIn('results', data)
        self.assertGreater(len(data['results']), 0)
        
        # Check that current application is not included
        returned_uids = [item['uid'] for item in data['results']]
        self.assertNotIn(str(application3.uid), returned_uids)

    def test_get_other_applications_schema_fields(self):
        """Test that the response contains the expected schema fields"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.application1.uid), headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        if len(data['results']) > 0:
            item = data['results'][0]
            expected_fields = [
                'uid', 'job_logo', 'role', 'location', 
                'job_stage', 'job_status', 'invited', 'applied_date', 'recruiter'
            ]
            
            for field in expected_fields:
                self.assertIn(field, item)

    def test_get_other_applications_pagination(self):
        """Test pagination functionality"""
        # Create many applications for the same talent
        for i in range(10):
            job = JobFactory.create(created_by=self.business_user)
            job_post = JobPostFactory.create(job=job)
            JobApplicationFactory.create(
                job_post=job_post,
                applicant=self.talent,
                recruiter=self.business_user
            )
        
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        
        # Get first application to test with
        first_app = JobApplication.objects.filter(
            applicant=self.talent,
            job_post__job__created_by__business=self.business
        ).first()
        
        response = self.client.get(self.url(first_app.uid), headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check pagination structure
        self.assertIn('results', data)
        self.assertIn('count', data)
        self.assertIn('next_page', data)
        self.assertIn('previous_page', data)
        self.assertIn('number_of_pages', data)


class EmploymentTypeListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/employment-types"

    def test_employment_type_list_endpoint(self):
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(data), 0)

    def test_employment_type_list_with_search(self):
        response = self.client.get(f"{self.url}?search=test")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 0)

class DepartmentListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/departments"

    def test_department_list_endpoint(self):
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(data), 0)

    def test_department_list_with_search(self):
        response = self.client.get(f"{self.url}?search=test")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 0)

class RoleListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/roles"

    def test_role_list_endpoint(self):
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(data), 2)

    def test_role_list_with_search(self):
        response = self.client.get(f"{self.url}?search=test")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 2)

class JobLevelListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/job-levels"

    def test_job_level_list_endpoint(self):
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(data), 0)

    def test_job_level_list_with_search(self):
        response = self.client.get(f"{self.url}?search=test")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 0)

class SkillCategoryListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/skill-categories"

    def test_skill_category_list_endpoint(self):
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 3)

    def test_skill_category_list_with_search(self):
        response = self.client.get(f"{self.url}?search=test")
        data = response.json()["data"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 3)

    def test_skill_category_list_with_category(self):
        test_name = SkillCategory.objects.first().name
        response = self.client.get(f"{self.url}?category={str(test_name).upper()}")
        data = response.json()["data"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 1)
        self.assertEqual(response.json()["data"][0]["category_name"], test_name)

    def test_skill_category_list_with_random_text(self):
        test_name = SkillCategory.objects.first().name[:6]
        response = self.client.get(f"{self.url}?category={test_name}")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 0)

class SkillListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/skills"

    def test_skill_list_endpoint(self):
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(data), 1)

    def test_skill_list_with_search(self):
        response = self.client.get(f"{self.url}?search=test")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(data), 1)

    def test_skill_list_with_category(self):
        test_name = SkillCategory.objects.first().name
        response = self.client.get(f"{self.url}?category={str(test_name).upper()}")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(data), 1)


    def test_skill_list_with_random_text(self):
        test_name = SkillCategory.objects.first().name[:6]
        response = self.client.get(f"{self.url}?category={test_name}")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 0)


class TestJobPostDetail(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        country = Country.objects.first()
        self.business = BusinessFactory.create()
        self.url = lambda post_uid: f"job-posts/{post_uid}"
        self.business_user = BusinessUserFactory.create(user=self.business.created_by, business=self.business)
        self.job = JobFactory.create(created_by=self.business_user)
        self.job_post = JobPostFactory.create(country=country,job=self.job, recruiter=self.business_user)
        self.talent = TalentFactory.create(country=country)


    def test_job_post_detail_endpoint_by_business_user(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["uid"], str(self.job_post.uid))

    def test_job_post_detail_endpoint_by_talent(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["uid"], str(self.job_post.uid))

    def test_wrong_uid(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid.uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_job_detail_from_another_business(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        business_user = BusinessUserFactory.create()
        job = self.job_post.job
        job.update(created_by=business_user)
        self.job_post.update(recruiter=business_user)
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 404)


class TestJobList(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        country = Country.objects.first()
        user = UserFactory.create()
        BusinessFactory.create()
        self.business = Business.objects.create(name="holly", created_by=user)
        self.url = ""
        self.business_user = BusinessUserFactory.create(user=self.business.created_by, business=self.business)

        jobs = JobFactory.create_batch(5, created_by=self.business_user)
        talents = TalentFactory.create_batch(5)
        for job in jobs:
            job_posts = JobPostFactory.create_batch(5, country=country, job=job, recruiter=self.business_user, status=JobStatusType.POSTED.value)
            for talent in talents:
                for job_post in job_posts[:choice(range(1,5))]:
                    stage = WorkflowStageFactory.create(created_by=self.business_user)
                    JobApplicationFactory.create(applicant=talent, job_post=job_post, stage=stage)

    def test_job_list_endpoint_by_business_user(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 5)
        self.assertIn("posts", response.data)
        self.assertIn("roles", response.data)

    def test_job_list_endpoint_by_talent(self):
        talent = TalentFactory.create()
        headers = {
            "authorization": f"bearer {talent.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_job_list_with_search(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        search = Job.objects.first().hiring_company_name
        response = self.client.get(f"{self.url}?search={search}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_job_list_with_status(self):
        status = JobStatusType.CLOSED.value
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"{self.url}?status={status}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        job_post = JobPost.objects.first()
        job_post.update(status=status)
        response = self.client.get(f"{self.url}?status={status}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)


class TestJobDetail(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        country = Country.objects.first()
        self.business = BusinessFactory.create()
        self.url = lambda post_uid: f"{post_uid}"
        self.business_user = BusinessUserFactory.create(user=self.business.created_by, business=self.business)
        self.job = JobFactory.create(created_by=self.business_user)
        self.talent = TalentFactory.create(country=country)

    def test_job_detail_endpoint_by_business_user(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["uid"], str(self.job.uid))

    def test_job_detail_endpoint_by_talent(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url(self.job.uid), headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_wrong_uid(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid.uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_job_by_another_business(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        business_user = BusinessUserFactory.create()
        self.job.update(created_by=business_user)
        response = self.client.get(self.url(self.job.uid), headers=headers)
        self.assertEqual(response.status_code, 404)


class TestApplicationList(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        country = Country.objects.first()
        self.business = BusinessFactory.create()
        self.url = lambda job_post_uid: f"job-posts/{job_post_uid}/applications"
        self.business_user = BusinessUserFactory.create(user=self.business.created_by, business=self.business)
        self.job = JobFactory.create(created_by=self.business_user)
        self.job_post = JobPostFactory.create(country=country, job=self.job, recruiter=self.business_user)
        for _ in range(10):
            stage = WorkflowStageFactory.create(created_by=self.business_user)
            if stage.phase == PhaseType.NEW.value:
                stage.update(phase=PhaseType.SCREENING.value)
            JobApplicationFactory.create(job_post=self.job_post, recruiter=self.business_user, stage=stage)

    def test_application_list_endpoint_by_business_user(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 10)
        self.assertEqual(response.data["count"], 10)


    def test_application_list_endpoint_by_talent(self):
        talent = TalentFactory.create()
        headers = {
            "authorization": f"bearer {talent.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 403)


    def test_wrong_uid(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid.uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_job_by_another_business(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_endpoint_with_phase_query(self):
        phase = PhaseType.HIRED.value
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"{self.url(self.job_post.uid)}?phase={phase}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        stage = WorkflowStageFactory.create(phase=phase, created_by=self.business_user)
        application = JobApplication.objects.first()
        application.update(stage=stage)
        response = self.client.get(f"{self.url(self.job_post.uid)}?phase={phase}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_endpoint_with_new_application_query(self):
        new_stage = WorkflowStageFactory.create(phase=PhaseType.NEW.value, created_by=self.business_user)
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"{self.url(self.job_post.uid)}?new_application=true", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        application = JobApplication.objects.first()
        application.update(stage=new_stage)
        response = self.client.get(f"{self.url(self.job_post.uid)}?new_application=true", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        response = self.client.get(f"{self.url(self.job_post.uid)}?new_application=false", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 9)

    def test_endpoint_with_sort_by_and_asc_query(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"{self.url(self.job_post.uid)}?sort_by=created_at&asc=true", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 10)
        self.assertLessEqual(response.data["results"][0]["created_at"], response.data["results"][1]["created_at"])

        response = self.client.get(f"{self.url(self.job_post.uid)}?sort_by=created_at&asc=false", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 10)
        self.assertGreaterEqual(response.data["results"][0]["created_at"], response.data["results"][1]["created_at"])

        response = self.client.get(f"{self.url(self.job_post.uid)}?sort_by=invited&asc=false", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 10)

    def test_endpoint_with_search_query(self):
        search = Talent.objects.last().user.first_name
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"{self.url(self.job_post.uid)}?search={search}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertLess(response.data["count"], 10)
        self.assertGreaterEqual(response.data["count"], 1)


class JobCreationTest(TestCase):

    def setUp(self):
        # Set up necessary data for the test
        self.skills = Skill.objects.all()[:5]
        self.business_models = BusinessModel.objects.all()[:5]
        self.language = Language.objects.create(name='English')
        self.education_level = EducationLevel.objects.first()
        self.employment_type = EmploymentType.objects.create(name='Full-time')
        industry = Industry.objects.create(name="Health")
        self.department = Department.objects.create(name='IT', industry=industry)
        self.role = Role.objects.create(name='Developer', department=self.department)
        self.job_level = JobLevel.objects.create(name='Junior')
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="testuser2@example.com",
            password="securepassword",
            type="BUSINESS"
        )
        self.business = Business.objects.create(name='Tech Corp', created_by=self.user)
        self.business_user = BusinessUser.objects.create(
            user=self.user,
            business=self.business,
        )
        self.recruiter = User.objects.create_user(
            first_name="Recruiter",
            last_name="Recruiter",
            email="testuser@example.com",
            password="securepassword",
        )
        self.qualification = "Bachelor's degree"
        self.recruiter_business_user = BusinessUser.objects.create(
            user=self.recruiter,
            business=self.business,
        )
        for phase in PhaseType.values():
            WorkflowStageFactory.create(phase=phase, created_by=self.business_user)

        self.auth = JWTAuth()
        self.client = TestClient(router)
        self.headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.country1 = Country.objects.order_by("?").first()
        self.country2 = Country.objects.order_by("?").first()  # random ordering
        self.province = State.objects.order_by("?").first()
        self.province2 = State.objects.order_by("?").first()
        self.currency1 = Currency.objects.order_by("?").first()
        self.currency2 = Currency.objects.order_by("?").first()
        self.test_data = {
            "title": "EcoTech Manager",
            "employment_type": str(self.employment_type.uid),
            "qualification": self.qualification,
            "availability": [
                {
                    "day": "Monday",
                    "start_time": "08:23:54.706000",
                    "active": True,
                    "end_time": "08:23:54.706000"
                },
                {
                    "day": "Tuesday",
                    "start_time": "08:23:54.706000",
                    "active": True,
                    "end_time": "08:23:54.706000"
                }
            ],
            "responsibilities": "".join(map(lambda x: f"<li>{x}</li>", [
                "Create innovative solutions to address environmental challenges",
                "Collaborate with cross-functional teams to design and implement sustainable solutions"
            ])),
            "hiring_company_name": "Gynex",
            "hiring_company_description": "EcoTech Solutions is a pioneering company in the field of sustainable technology, dedicated to developing innovative products and services that promote environmental responsibility and reduce the carbon footprint of individuals and businesses. Founded in 2010, EcoTech Solutions has grown from a small startup into a global leader in green technology, with a mission to make sustainability accessible and affordable for everyone",
            "work_structure": "remote",
            "minimum_education_level": str(self.education_level.uid),
            "technological_requirement": "macbook",
            "first_language": str(self.language.uid),
            "additional_languages": [
                str(self.language.uid)
            ],
            "lunch_break": "paid",
            "lunch_break_time": 30,
            "office_address": "123 Main St, AnyTown, USA",
            "additional_hours_start": "12:00:00",
            "additional_hours_end": "22:00:00",
            "business_models": list(self.business_models.values_list("uid", flat=True)),
            "job_posts": [
                {
                    "country": str(self.country1.uid),
                    "province": str(self.province.uid),
                    "city": "surulere",
                    "postal_code": "500000",
                    "share_compensation": True,
                    "status": JobStatusType.POSTED.value,
                    "benefits": [
                        "Health Insurance",
                        "Dental Insurance"
                    ],

                    "salary_min": 100,
                    "salary_max": 1000,
                    "salary_type": "Weekly",
                    "salary_bonus_type": "Weekly",
                    
                    "salary_currency": str(self.currency1.uid),
                    "salary_bonus_min": 100,
                    "salary_bonus_max": 150,
                    "recruiter": str(self.business_user.uid),
                    "salary_bonus_currency": str(self.currency1.uid)

                },
                {
                    "country": str(self.country2.uid),
                    "province": str(self.province.uid),
                    "city": "ojo",
                    "postal_code": "500000",
                    "share_compensation": False,
                    "benefits": [
                        "Health Insurance",
                        "Dental Insurance"
                    ],
                    "salary_min": 200,
                    "salary_max": 400,
                    "salary_type": "Weekly",
                    "salary_bonus_type": "Weekly",
                    "salary_currency": str(self.currency2.uid),
                    "salary_bonus_min": 100,
                    "salary_bonus_max": 150,
                    "salary_bonus_currency": str(self.currency2.uid),
                    "recruiter": str(self.business_user.uid),

                }
            ],
            "screening_questions": [
                {
                    "type": "single select",
                    "options": [
                        {
                            "is_accepted": True,
                            "text": "yes"
                        },
                        {
                            "is_accepted": False,
                            "text": "No"
                        }
                    ],
                    "text": "Are you eligible to work in the US?"
                },
            ],
            "department": str(self.department.uid),
            "role": str(self.role.uid),
            "skills": [
                str(skill.uid) for skill in self.skills
            ],
            "job_level": str(self.job_level.uid)
        }

    def test_create_job_without_complete_stage(self):
        from settings.models import WorkFlowStage
        WorkFlowStage.objects.filter(created_by__business=self.business).delete()
        response = self.client.post("", json=self.test_data, headers=self.headers)
        self.assertEqual(response.status_code, 400)


    def test_create_job(self):
        response = self.client.post("", json=self.test_data, headers=self.headers)
        # Assert the job was created correctly
        self.assertEqual(response.status_code, 200)
        job = Job.objects.filter(created_by=self.business_user).first()

        self.assertEqual(job.created_by, self.business_user)
        self.assertEqual(job.first_language, self.language)
        self.assertEqual(job.employment_type, self.employment_type)
        self.assertEqual(job.role, self.role)
        self.assertEqual(job.job_level, self.job_level)

        # Check availability
        available_days = AvailableDay.objects.filter(job=job)
        self.assertEqual(available_days.count(), 2)

        # Check job posts
        job_posts = JobPost.objects.filter(job=job).order_by("id")
        self.assertEqual(job_posts.count(), 2)
        self.assertEqual(job_posts[0].city, "surulere")
        self.assertEqual(job_posts[1].city, "ojo")
        self.assertEqual(job_posts[0].country.code, self.country1.code)

        # Check screening questions
        screening_questions = ScreeningQuestion.objects.filter(job=job).order_by("id")
        self.assertEqual(screening_questions.count(), 1)
        self.assertEqual(screening_questions[0].text, 'Are you eligible to work in the US?')
        self.assertFalse(screening_questions[0].is_knockout)

        # Check question options
        question_options = QuestionOption.objects.filter(question=screening_questions[0])
        self.assertEqual(question_options.count(), 2)
        self.assertEqual(job.skills.count(), 5)

    def test_create_job_by_talent(self):
        talent = TalentFactory.create()
        header = {"Authorization": f"Bearer {talent.user.token}"}
        response = self.client.post("", json=self.test_data, headers=header)
        self.assertEqual(response.status_code, 403)

    def test_without_hiring_company_details(self):
        self.test_data["hiring_company_name"] = None
        self.test_data["hiring_company_description"] = None
        response = self.client.post("", json=self.test_data, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        job = Job.objects.filter(created_by=self.business_user).last()
        self.assertEqual(job.hiring_company_name, self.business.name)
        self.assertEqual(job.hiring_company_description, self.business.description)


class JobUpdateTest(TestCase):

    def setUp(self):
        self.currency = CurrencyFactory.create()
        self.country = Country.objects.order_by("?").first()
        # Set up necessary data for the test
        self.user = UserFactory.create()
        self.business = BusinessFactory.create(created_by=self.user)
        self.business_user = BusinessUserFactory.create(
            user=self.user,
            business=self.business,
        )
        self.url = lambda job_uid: f"{job_uid}"
        self.auth = JWTAuth()
        self.client = TestClient(router)
        self.job = JobFactory.create(created_by=self.business_user)
        self.job_posts = JobPostFactory.create_batch(2, job=self.job)
        self.test_data = {
            "availability": [
                {
                    "day": "Monday",
                    "start_time": "08:23:54.706000",
                    "active": True,
                    "end_time": "08:23:54.706000"
                },
                {
                    "day": "Tuesday",
                    "start_time": "08:23:54.706000",
                    "active": True,
                    "end_time": "08:23:54.706000"
                }
            ],
            "responsibilities": "".join(map(lambda x: f"<li>{x}</li>",[
                "Create innovative solutions to address environmental challenges",
                "Collaborate with cross-functional teams to design and implement sustainable solutions"
            ])),
            "hiring_company_name": "Gynex",
            "hiring_company_description": "EcoTech Solutions is a pioneering company in the field of sustainable technology, dedicated to developing innovative products and services that promote environmental responsibility and reduce the carbon footprint of individuals and businesses. Founded in 2010, EcoTech Solutions has grown from a small startup into a global leader in green technology, with a mission to make sustainability accessible and affordable for everyone",
            "work_structure": "remote",
            "technological_requirement": "macbook",
            "lunch_break": "paid",
            "lunch_break_time": 30,
            "job_posts": [
                {
                    "uid": self.job_posts[0].uid,
                    "benefits": [
                        "Holiday",
                        "Paid time off"
                    ],
                    "city": "ojo",
                    "status": JobStatusType.DRAFT.value,
                    "salary_currency": str(self.currency.uid),
                    "salary_bonus_currency": str(self.currency.uid),
                    "salary_min": 100,
                    "salary_type": "Hourly",
                    "salary_bonus_type": "Hourly",
                    "salary_max": 1000,
                    "salary_bonus_min": 200,
                    "salary_bonus_max": 2000
                }
            ],
            "additional_hours_start": "12:00:00",
            "additional_hours_end": "22:00:00"
        }

    def test_update_job(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }

        available_days = AvailableDay.objects.filter(job=self.job)
        self.assertEqual(available_days.count(), 0)
        title = self.job.title
        office_address = self.job.office_address
        self.assertNotEqual(self.job.hiring_company_name, self.test_data["hiring_company_name"])
        self.assertNotEqual(self.job.hiring_company_description, self.test_data["hiring_company_description"])

        response = self.client.patch(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)

        self.job.refresh_from_db()

        self.assertEqual(self.job.title, title)
        self.assertEqual(self.job.hiring_company_name, self.test_data["hiring_company_name"])
        self.assertEqual(self.job.hiring_company_description, self.test_data["hiring_company_description"])
        self.assertEqual(self.job.work_structure, self.test_data["work_structure"])
        self.assertEqual(self.job.technological_requirement, self.test_data["technological_requirement"])
        self.assertEqual(self.job.lunch_break, self.test_data["lunch_break"])
        self.assertEqual(self.job.lunch_break_time, self.test_data["lunch_break_time"])
        self.assertEqual(self.job.office_address, office_address)
        self.assertEqual(str(self.job.additional_hours_start), self.test_data["additional_hours_start"])
        self.assertEqual(str(self.job.additional_hours_end), self.test_data["additional_hours_end"]),

        job_post = self.job_posts[0]
        job_post.refresh_from_db()
        self.assertEqual(job_post.city, "ojo")
        self.assertEqual(job_post.benefits, self.test_data["job_posts"][0]["benefits"])
        self.assertEqual(job_post.status, self.test_data["job_posts"][0]["status"])
        self.assertEqual(str(job_post.salary_currency.uid), self.test_data["job_posts"][0]["salary_currency"])
        self.assertEqual(str(job_post.salary_bonus_currency.uid), self.test_data["job_posts"][0]["salary_bonus_currency"])
        self.assertEqual(job_post.salary_min, self.test_data["job_posts"][0]["salary_min"])
        self.assertEqual(job_post.salary_max, self.test_data["job_posts"][0]["salary_max"])
        self.assertEqual(job_post.salary_bonus_min, self.test_data["job_posts"][0]["salary_bonus_min"])
        self.assertEqual(job_post.salary_bonus_max, self.test_data["job_posts"][0]["salary_bonus_max"])

        available_days = AvailableDay.objects.filter(job=self.job)
        self.assertEqual(available_days.count(), 2)

    def test_update_job_with_multiple_job_posts(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.test_data["job_posts"] = [
            {
                "uid": self.job_posts[0].uid,
                "benefits": [
                    "Holiday",
                    "Paid time off"
                ],
                "status": JobStatusType.CLOSED.value,
                "salary_currency": str(self.currency.uid),
                "salary_bonus_currency": str(self.currency.uid),
                "salary_min": 100,
                "salary_max": 1000,
                "salary_type": "Monthly",
                "salary_bonus_type": "Monthly",
                "salary_bonus_min": 3000,
                "salary_bonus_max": 4000
            },
            {
                "uid": self.job_posts[1].uid,
                "benefits": [
                    "Holiday",
                    "Paid time off"
                ],
                "country": str(self.job_posts[0].country.uid),
                "salary_currency": str(self.currency.uid),
                "salary_bonus_currency": str(self.currency.uid),
                "salary_min": 100,
                "salary_max": 1000,
                "salary_type": "Weekly",
                "salary_bonus_type": "Weekly",
                "salary_bonus_min": 200,
                "salary_bonus_max": 2000
            },
            {
                "benefits": [
                    "Holiday",
                    "Paid time off"
                ],
                "country": str(self.country.uid),
                "salary_currency": str(self.currency.uid),
                "salary_bonus_currency": str(self.currency.uid),
                "salary_min": 500,
                "salary_max": 1000,
                "salary_bonus_min": 200,
                "salary_bonus_max": 5000
            }
        ]

        available_days = AvailableDay.objects.filter(job=self.job)
        self.assertEqual(available_days.count(), 0)
        title = self.job.title
        office_address = self.job.office_address
        self.assertNotEqual(self.job.hiring_company_name, self.test_data["hiring_company_name"])
        self.assertNotEqual(self.job.hiring_company_description, self.test_data["hiring_company_description"])

        response = self.client.patch(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)

        self.job.refresh_from_db()

        self.assertEqual(self.job.title, title)
        self.assertEqual(self.job.hiring_company_name, self.test_data["hiring_company_name"])
        self.assertEqual(self.job.hiring_company_description, self.test_data["hiring_company_description"])
        self.assertEqual(self.job.work_structure, self.test_data["work_structure"])
        self.assertEqual(self.job.technological_requirement, self.test_data["technological_requirement"])
        self.assertEqual(self.job.lunch_break, self.test_data["lunch_break"])
        self.assertEqual(self.job.lunch_break_time, self.test_data["lunch_break_time"])
        self.assertEqual(self.job.office_address, office_address)
        self.assertEqual(str(self.job.additional_hours_start), self.test_data["additional_hours_start"])
        self.assertEqual(str(self.job.additional_hours_end), self.test_data["additional_hours_end"]),

        job_post = self.job_posts[0]
        job_post.refresh_from_db()
        self.assertEqual(job_post.benefits, self.test_data["job_posts"][0]["benefits"])
        self.assertEqual(job_post.status, self.test_data["job_posts"][0]["status"])
        self.assertEqual(str(job_post.salary_currency.uid), self.test_data["job_posts"][0]["salary_currency"])
        self.assertEqual(str(job_post.salary_bonus_currency.uid), self.test_data["job_posts"][0]["salary_bonus_currency"])
        self.assertEqual(job_post.salary_min, self.test_data["job_posts"][0]["salary_min"])
        self.assertEqual(job_post.salary_max, self.test_data["job_posts"][0]["salary_max"])
        self.assertEqual(job_post.salary_bonus_min, self.test_data["job_posts"][0]["salary_bonus_min"])
        self.assertEqual(job_post.salary_bonus_max, self.test_data["job_posts"][0]["salary_bonus_max"])

        job_post = self.job_posts[1]
        job_post.refresh_from_db()
        self.assertEqual(job_post.benefits, self.test_data["job_posts"][1]["benefits"])
        self.assertEqual(str(job_post.country.uid), self.test_data["job_posts"][1]["country"])
        self.assertEqual(str(job_post.salary_currency.uid), self.test_data["job_posts"][1]["salary_currency"])
        self.assertEqual(str(job_post.salary_bonus_currency.uid), self.test_data["job_posts"][1]["salary_bonus_currency"])
        self.assertEqual(job_post.salary_min, self.test_data["job_posts"][1]["salary_min"])
        self.assertEqual(job_post.salary_max, self.test_data["job_posts"][1]["salary_max"])
        self.assertEqual(job_post.salary_bonus_min, self.test_data["job_posts"][1]["salary_bonus_min"])
        self.assertEqual(job_post.salary_bonus_max, self.test_data["job_posts"][1]["salary_bonus_max"])


        available_days = AvailableDay.objects.filter(job=self.job)
        self.assertEqual(available_days.count(), 2)
        self.assertEqual(JobPost.objects.count(), 3)

    def test_update_job_by_talent(self):
        talent = TalentFactory.create()
        headers = {"Authorization": f"Bearer {talent.user.token}"}
        response = self.client.patch(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_without_hiring_company_details(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.test_data["hiring_company_name"] = None
        self.test_data["hiring_company_description"] = None
        response = self.client.patch(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.hiring_company_name, self.business.name)
        self.assertEqual(self.job.hiring_company_description, self.business.description)

    def test_update_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.patch(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_update_job_with_invalid_uuid(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.patch(self.url(uuid4()), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)


class JobPostCreationTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.business = BusinessFactory.create(created_by=self.user)
        self.business_user = BusinessUserFactory.create(business=self.business, user=self.user)
        self.job = JobFactory.create(created_by=self.business_user)
        self.auth = JWTAuth()
        self.client = TestClient(router)
        self.url = lambda job_uid: f"{job_uid}/job-post"
        self.country = Country.objects.first()
        self.city = City.objects.first()
        self.province = State.objects.first()
        self.currency = Currency.objects.first()
        self.test_data = {
                  "country": str(self.country.uid),
                  "benefits": [
                    "Holiday",
                    "Paid time off"
                  ],
                  "recruiter": str(self.business_user.uid),
                  "status": JobStatusType.POSTED.value,
                  "salary_currency": str(self.currency.uid),
                  "salary_bonus_currency": str(self.currency.uid),
                  "province": str(self.province.uid),
                  "postal_code": "12345",
                  "share_compensation": True,
                  "salary_min": 100,
                  "salary_max": 1000,
                  "salary_bonus_min": 200,
                  "salary_bonus_max": 2000,
                  "tags": [
                    "test1",
                    "test2",
                    "test3"
                  ],
                }

    def test_create_job_post(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.post(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)

        job_post = JobPost.objects.filter(job=self.job).first()

        self.assertEqual(job_post.country, self.country)
        self.assertEqual(job_post.benefits, self.test_data["benefits"])
        self.assertEqual(job_post.recruiter, self.business_user)
        self.assertEqual(job_post.status, self.test_data["status"])
        self.assertEqual(job_post.salary_currency, self.currency)
        self.assertEqual(job_post.salary_bonus_currency, self.currency)
        self.assertEqual(job_post.province, self.province)
        self.assertEqual(job_post.postal_code, self.test_data["postal_code"])
        self.assertEqual(job_post.share_compensation, self.test_data["share_compensation"])
        self.assertEqual(job_post.salary_min, self.test_data["salary_min"])
        self.assertEqual(job_post.salary_max, self.test_data["salary_max"])
        self.assertEqual(job_post.salary_bonus_min, self.test_data["salary_bonus_min"])
        self.assertEqual(job_post.salary_bonus_max, self.test_data["salary_bonus_max"])
        self.assertEqual(job_post.posted_by, self.business_user)
        self.assertEqual(job_post.tags.filter(name__in=self.test_data["tags"]).count(), 3)


    def test_create_job_post_with_invalid_uuid(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.post(self.url(uuid4()), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_create_job_post_with_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.post(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_create_job_post_by_talent(self):
        talent = TalentFactory.create()
        headers = {"Authorization": f"Bearer {talent.user.token}"}
        response = self.client.post(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 403)

class JobPostUpdateTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.business = BusinessFactory.create(created_by=self.user)
        self.business_user = BusinessUserFactory.create(business=self.business, user=self.user)
        self.job = JobFactory.create(created_by=self.business_user)
        self.auth = JWTAuth()
        self.client = TestClient(router)
        self.country = Country.objects.first()
        self.currency = Currency.objects.first()
        self.job_post = JobPostFactory.create(job=self.job, country=self.country, status=JobStatusType.POSTED.value)
        self.job_post.tags.add(JobPostTag.objects.create(name="test1", business=self.business))
        self.job_post.tags.add(JobPostTag.objects.create(name="test2", business=self.business))
        self.job_post.tags.add(JobPostTag.objects.create(name="test3", business=self.business))
        self.job_post.save()
        self.url = lambda job_post_uid: f"job-post/{job_post_uid}"
        self.test_data = {
            "benefits": [
                "Holiday",
                "Paid time off"
            ],
            "status": JobStatusType.DRAFT.value,
            "salary_currency": str(self.currency.uid),
            "salary_bonus_currency": str(self.currency.uid),
            "salary_min": 100,
            "salary_type": "Weekly",
            "salary_bonus_type": "Weekly",
            "salary_max": 1000,
            "salary_bonus_min": 200,
            "salary_bonus_max": 2000,
            "tags": [
                "test7",
                "test2",
                "test5"
            ]
        }

    def test_update_job_post(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }

        self.assertNotEqual(self.job_post.status, self.test_data["status"])
        self.assertNotEqual(self.job_post.salary_currency, self.currency.abbreviation)
        self.assertNotEqual(self.job_post.salary_bonus_currency, self.currency.abbreviation)
        self.assertNotEqual(self.job_post.salary_min, self.test_data["salary_min"])
        self.assertNotEqual(self.job_post.salary_max, self.test_data["salary_max"])
        self.assertNotEqual(self.job_post.salary_bonus_min, self.test_data["salary_bonus_min"])
        self.assertNotEqual(self.job_post.salary_bonus_max, self.test_data["salary_bonus_max"])

        response = self.client.patch(self.url(self.job_post.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)

        self.job_post.refresh_from_db()

        data = response.json()

        # check details of old job poast
        self.assertEqual(self.test_data["status"], data["status"])
        self.assertNotEqual(str(self.job_post.uid), data["uid"])
        self.assertEqual(data["benefits"], self.test_data["benefits"])
        self.assertEqual(self.job_post.status, "closed")
        self.assertEqual(self.job_post.tags.filter(name__in=self.test_data["tags"]).count(), 1)
        self.assertEqual(self.job_post.tags.filter(name__in=["test1", "test2", "test3"]).count(), 3)

        # check details of new job post
        self.assertEqual(data["salary_currency"], self.currency.abbreviation)
        self.assertEqual(data["salary_bonus_currency"], self.currency.abbreviation)
        self.assertEqual(data["salary_min"], self.test_data["salary_min"])
        self.assertEqual(data["salary_max"], self.test_data["salary_max"])
        self.assertEqual(data["salary_bonus_min"], self.test_data["salary_bonus_min"])
        self.assertEqual(data["salary_bonus_max"], self.test_data["salary_bonus_max"])
        job_post = JobPost.objects.get(uid=data["uid"])
        self.assertEqual(job_post.tags.filter(name__in=self.test_data["tags"]).count(), 3)
        self.assertEqual(job_post.tags.filter(name__in=["test1", "test2", "test3"]).count(), 1)



    def test_update_job_post_to_posted(self):
        self.job_post.update(status=JobStatusType.PAUSED.value, date_posted=timezone.now() - timedelta(days=6))
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.test_data["status"] = JobStatusType.POSTED.value


        response = self.client.patch(self.url(self.job_post.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)

        self.job_post.refresh_from_db()
        data = response.json()
        self.assertEqual(self.test_data["status"], data["status"])
        self.assertEqual(str(self.job_post.uid), data["uid"])
        self.assertEqual(self.job_post.date_posted.date(), timezone.now().date())

    def test_update_job_post_with_invalid_uuid(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.patch(self.url(uuid4()), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_update_job_post_with_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.patch(self.url(self.job_post.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_update_job_post_by_talent(self):
        talent = TalentFactory.create()
        headers = {"Authorization": f"Bearer {talent.user.token}"}
        response = self.client.patch(self.url(self.job_post.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 403)



class JobPostDeleteTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.business = BusinessFactory.create(created_by=self.user)
        self.business_user = BusinessUserFactory.create(business=self.business, user=self.user)
        self.job = JobFactory.create(created_by=self.business_user)
        self.auth = JWTAuth()
        self.client = TestClient(router)
        self.country = Country.objects.first()
        self.currency = Currency.objects.first()
        self.job_post = JobPostFactory.create(job=self.job, country=self.country, status=JobStatusType.POSTED.value)
        self.job_post.tags.add(JobPostTag.objects.create(name="test1", business=self.business))
        self.job_post.tags.add(JobPostTag.objects.create(name="test2", business=self.business))
        self.job_post.tags.add(JobPostTag.objects.create(name="test3", business=self.business))
        self.job_post.save()
        self.url = lambda job_post_uid: f"job-post/{job_post_uid}"

    def test_delete_job_post(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.delete(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 204)

        job_post = JobPost.objects.filter(uid=self.job_post.uid).first()
        self.assertIsNone(job_post)
        self.assertEqual(self.job_post.tags.filter(name__in=["test1", "test2", "test3"]).count(), 0)

    def test_delete_job_post_with_invalid_uuid(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.delete(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_delete_job_post_with_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.delete(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_delete_job_post_by_talent(self):
        talent = TalentFactory.create()
        headers = {"Authorization": f"Bearer {talent.user.token}"}
        response = self.client.delete(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 403)

class SetJobRequirementTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.job.requiredattribute.hard_delete()
        self.job.refresh_from_db()
        self.url = lambda job_uid : f"{job_uid}/required-attributes"
        self.skills = Skill.objects.all()[:1]
        self.business_models = BusinessModel.objects.all()[:1]
        self.languages = Language.objects.all()[:1]
        self.test_data = {
            "skills": list(map(lambda x: str(x.uid), self.skills)),
            "business_models": list(map(lambda x:str(x.uid), self.business_models)),
            "role": False,
            "job_level": False,
            "years_of_experience": False,
            "minimum_education_level": False,
            "work_structure": False,
            "technological_requirement": True,
            "first_language": True,
            "secondary_language": False,
            "working_hours": False,
            "location": False,
            "secondary_languages": list(map(lambda x: str(x.uid), self.languages)),
        }

    def test_set_job_required_attributes(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        self.assertFalse(hasattr(self.job, "requiredattribute"))
        response = self.client.patch(self.url(self.job.uid), headers=headers, json=self.test_data)
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertTrue(hasattr(self.job, "requiredattribute"))
        required_attributes = self.job.requiredattribute
        self.assertTrue(required_attributes.skills.filter(uid__in=self.test_data["skills"]).exists())
        self.assertTrue(required_attributes.skills.count(), len(self.test_data["skills"]))
        self.assertTrue(required_attributes.business_models.filter(uid__in=self.test_data["business_models"]).exists())
        self.assertTrue(required_attributes.business_models.count(), len(self.test_data["business_models"]))
        self.assertEqual(required_attributes.role, self.test_data["role"])
        self.assertEqual(required_attributes.job_level, self.test_data["job_level"])
        self.assertEqual(required_attributes.years_of_experience, self.test_data["years_of_experience"])
        self.assertEqual(required_attributes.minimum_education_level, self.test_data["minimum_education_level"])
        self.assertEqual(required_attributes.work_structure, self.test_data["work_structure"])
        self.assertEqual(required_attributes.technological_requirement, self.test_data["technological_requirement"])
        self.assertEqual(required_attributes.first_language, self.test_data["first_language"])
        self.assertEqual(required_attributes.secondary_language, self.test_data["secondary_language"])
        self.assertEqual(required_attributes.working_hours, self.test_data["working_hours"])
        self.assertEqual(required_attributes.location, self.test_data["location"])

    def test_set_job_required_attributes_with_attributes(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        _required_attributes = RequiredAttributeFactory.create(job=self.job)
        response = self.client.patch(self.url(self.job.uid), headers=headers, json=self.test_data)
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertTrue(hasattr(self.job, "requiredattribute"))
        required_attributes = self.job.requiredattribute
        self.assertEqual(_required_attributes.uid, required_attributes.uid)
        self.assertEqual(
            RequiredSkill.objects.filter(skill__uid__in=self.test_data["skills"]).count(), 
            len(self.test_data["skills"])
        )
        self.assertTrue(required_attributes.skills.count(), len(self.test_data["skills"]))
        self.assertTrue(required_attributes.business_models.filter(uid__in=self.test_data["business_models"]).exists())
        self.assertTrue(required_attributes.business_models.count(), len(self.test_data["business_models"]))
        self.assertEqual(required_attributes.role, self.test_data["role"])
        self.assertEqual(required_attributes.job_level, self.test_data["job_level"])
        self.assertEqual(required_attributes.years_of_experience, self.test_data["years_of_experience"])
        self.assertEqual(required_attributes.minimum_education_level, self.test_data["minimum_education_level"])
        self.assertEqual(required_attributes.work_structure, self.test_data["work_structure"])
        self.assertEqual(required_attributes.technological_requirement, self.test_data["technological_requirement"])
        self.assertEqual(required_attributes.first_language, self.test_data["first_language"])
        self.assertEqual(required_attributes.secondary_language, self.test_data["secondary_language"])
        self.assertEqual(required_attributes.working_hours, self.test_data["working_hours"])
        self.assertEqual(required_attributes.location, self.test_data["location"])

    def test_set_job_required_attributes_with_invalid_uuid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.patch(self.url(uuid4()), headers=headers, json=self.test_data)
        self.assertEqual(response.status_code, 404)

    def test_set_job_required_attributes_by_talent(self):
        talent = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent.user.token}"
        }
        response = self.client.patch(self.url(self.job.uid), headers=headers, json=self.test_data)
        self.assertEqual(response.status_code, 403)

    def test_set_job_required_attributes_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.patch(self.url(self.job.uid), headers=headers, json=self.test_data)
        self.assertEqual(response.status_code, 404)


class GetJobRequirementTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.job.requiredattribute.hard_delete()
        self.job.refresh_from_db()
        self.url = lambda job_uid: f"{job_uid}/required-attributes"

    def test_job_without_required_attributes(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        self.assertFalse(hasattr(self.job, "requiredattribute"))
        response = self.client.get(self.url(self.job.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertTrue(hasattr(self.job, "requiredattribute"))
        self.assertEqual(str(self.job.requiredattribute.uid), response.data["uid"])

    def test_job_with_required_attributes(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(str(self.job.requiredattribute.uid), response.data["uid"])


    def test_get_job_required_attributes_with_invalid_uuid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)


    def test_get_job_required_attributes_by_talent(self):
        talent = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent.user.token}"
        }
        response = self.client.get(self.url(self.job.uid), headers=headers)
        self.assertEqual(response.status_code, 403)


    def test_get_job_required_attributes_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.get(self.url(self.job.uid), headers=headers)
        self.assertEqual(response.status_code, 404)

class TalentsByJobPostTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = CountryFactory.create()
        self.business_user = BusinessUserFactory.create()
        
        # Create talents with different match profiles
        self.talent1 = TalentFactory.create(country=self.country, visible=True)
        self.talent2 = TalentFactory.create(country=self.country, visible=True)
        self.talent3 = TalentFactory.create(country=self.country, visible=False)  # invisible
        self.talent4 = TalentFactory.create(visible=True)  # different country
        
        # Create job with required attributes
        self.job = JobFactory.create(created_by=self.business_user)
        self.job.requiredattribute.update(location=True)
        self.job_post = JobPostFactory.create(job=self.job, country=self.country)
        self.url = lambda job_post_uid: f"job-posts/{job_post_uid}/talents"

    def test_get_talents_by_job_post(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_only_visible_talents_returned(self):
        """Only talents with visible=True should be returned"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        
        returned_uids = [item['uid'] for item in response.json()]
        # talent3 is invisible, should not be in results
        self.assertNotIn(str(self.talent3.uid), returned_uids)

    def test_talents_ordered_by_match_score(self):
        """Talents should be ordered by computed_match_score descending"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        if len(data) > 1:
            match_scores = [item.get('match_score', 0) or 0 for item in data]
            # Verify descending order
            self.assertEqual(match_scores, sorted(match_scores, reverse=True))

    def test_search_by_first_name(self):
        """Search should filter by talent's first name"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        search_query = self.talent1.user.first_name
        response = self.client.get(self.url(self.job_post.uid)+f"?search={search_query}", headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        # If results exist, verify the searched name is in results
        if data:
            first_names = [item['first_name'] for item in data]
            self.assertTrue(any(search_query.lower() in name.lower() for name in first_names))

    def test_search_by_email(self):
        """Search should filter by talent's email"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        search_query = self.talent1.user.email.split('@')[0]  # Use part of email
        response = self.client.get(self.url(self.job_post.uid)+f"?search={search_query}", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_search_with_multiple_terms(self):
        """Search with multiple space-separated terms should work"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        # Search with first name and last name
        search_query = f"{self.talent1.user.first_name} {self.talent1.user.last_name}"
        response = self.client.get(self.url(self.job_post.uid)+f"?search={search_query}", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_search_returns_empty_for_no_match(self):
        """Search with non-existent name should return empty list"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid)+"?search=NonExistentNameXYZ123", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_invalid_job_post_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_get_talents_by_job_post_by_talent(self):
        """Talent users should not have access to this endpoint"""
        headers = {
            "authorization": f"Bearer {self.talent1.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_get_talents_by_job_post_by_another_business_user(self):
        """Business users from other businesses should not access job posts"""
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_response_includes_required_fields(self):
        """Response should include all required schema fields"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        if data:
            first_item = data[0]
            required_fields = ['uid', 'first_name', 'last_name', 'user_uid', 'email', 'match_score']
            for field in required_fields:
                self.assertIn(field, first_item)

    def test_minimum_match_score_filter(self):
        """Only talents with match_score >= 50 should be returned"""
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        for item in data:
            match_score = item.get('match_score', 0)
            if match_score is not None:
                self.assertGreaterEqual(match_score, 50)

    def test_job_post_without_required_attributes(self):
        """Job posts without required attributes should still return talents"""
        job_no_req = JobFactory.create(created_by=self.business_user)
        job_post_no_req = JobPostFactory.create(job=job_no_req, country=self.country)
        
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(job_post_no_req.uid), headers=headers)
        self.assertEqual(response.status_code, 200)

class AddScreeningQuestionTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.url = lambda job_uid: f"{job_uid}/screening-questions"
        self.test_data = {
              "type": "single select",
              "options": [
                {
                  "is_accepted": True,
                  "text": "Louis"
                },
                  {
                      "is_accepted": False,
                      "text": "Kehinde"
                  }
              ],
              "text": "What is my name?",
              "is_knockout": True
            }

    def test_add_screening_question(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.job.screeningquestion_set.count(), 1)


    def test_file_question_with_options(self):
        self.test_data["type"] = QuestionTypeEnum.FILE.value
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_invalid_job_id(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(uuid4()), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.post(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_single_select_question_with_2_correct_options(self):
        self.test_data["type"] = QuestionTypeEnum.SINGLE_SELECT.value
        self.test_data["options"][0]["is_accepted"] = True
        self.test_data["options"][1]["is_accepted"] = True
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_multi_select_question_with_only_one_correct_option(self):
        self.test_data["type"] = QuestionTypeEnum.MULTI_SELECT.value
        self.test_data["options"][0]["is_accepted"] = True
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.job.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)


class UpdateScreeningQuestionTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.url = lambda question_uid: f"screening-questions/{question_uid}"
        self.screening_question = ScreeningQuestionFactory.create(job=self.job, type=QuestionTypeEnum.SINGLE_SELECT.value,
                                                                  is_knockout=True)
        self.test_data = {
            "type": "single select",
            "text": "What is her name?",
            "is_knockout": True
        }

    def test_update_screening_question(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.patch(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.screening_question.refresh_from_db()
        self.assertEqual(self.screening_question.text, self.test_data["text"])

    def test_update_to_multiselect_with_one_correct_option(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        self.test_data["type"] = QuestionTypeEnum.MULTI_SELECT.value
        response = self.client.patch(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_update_to_file_question(self):
        self.test_data["type"] = QuestionTypeEnum.FILE.value
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.patch(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_update_with_invalid_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.patch(self.url(uuid.uuid4()), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_update_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.patch(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)


class MutateScreeningQuestionOptionsTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.url = lambda question_uid: f"screening-questions/{question_uid}/options"
        self.screening_question = ScreeningQuestionFactory.create(job=self.job,
                                                                  is_knockout=True,
                                                                  type=QuestionTypeEnum.SINGLE_SELECT.value)
        self.test_data = [
                {
                    "is_accepted": False,
                    "text": "Louis"
                },
                {
                    "is_accepted": False,
                    "text": "Kehinde"
                }
            ]

    def test_mutate_screening_question_options(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        previous_options = self.screening_question.options().count()
        response = self.client.post(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.screening_question.refresh_from_db()
        self.assertEqual(self.screening_question.options().count(), previous_options + 2)

    def test_single_select_question_with_2_correct_options(self):
        self.test_data[0]["is_accepted"] = True
        self.test_data[1]["is_accepted"] = True
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_multi_select_question_with_only_one_correct_option(self):
        self.screening_question.update(type=QuestionTypeEnum.MULTI_SELECT.value, is_knockout=True)
        self.screening_question.refresh_from_db()
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_multi_select_with_2_correct_options(self):
        self.screening_question.update(type=QuestionTypeEnum.MULTI_SELECT.value)
        self.screening_question.refresh_from_db()
        self.test_data[0]["is_accepted"] = True
        self.test_data[1]["is_accepted"] = True
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.screening_question.refresh_from_db()
        self.assertEqual(self.screening_question.options().filter(is_accepted=True).count(), 3)

    def test_with_invalid_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.post(self.url(uuid.uuid4()), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.post(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_by_talent(self):
        talent_user = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent_user.user.token}"
        }
        response = self.client.post(self.url(self.screening_question.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 403)

class DeleteScreeningQuestionOptionsTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.url = lambda question_uid: f"screening-questions/{question_uid}/options"
        self.question = ScreeningQuestionFactory.create(job=self.job, type=QuestionTypeEnum.SINGLE_SELECT.value)
        self.option = self.question.questionoption_set.filter(is_accepted=False).first()
        self.test_data = [str(self.option.uid)]

    def test_delete_options(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        previous_options = self.question.options().count()
        response = self.client.delete(self.url(self.question.uid),  json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.question.refresh_from_db()
        self.assertEqual(self.question.options().count(), previous_options -1)

    def test_delete_correct_option_from_single_select(self):
        correct_option = self.question.questionoption_set.filter(is_accepted=True).first()
        self.test_data.append(str(correct_option.uid))
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url(self.question.uid),  json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_delete_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.delete(self.url(self.question.uid),  json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_delete_with_invalid_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url(uuid.uuid4()),  json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_delete_all_correct_options_in_multi_select(self):
        self.question.update(type=QuestionTypeEnum.MULTI_SELECT.value)
        incorrect_option = self.question.questionoption_set.filter(is_accepted=False).first()
        incorrect_option.update(is_correct=True)
        self.question.refresh_from_db()
        correct_options = self.question.questionoption_set.filter(is_accepted=True).all()
        self.test_data = [str(option.uid) for option in correct_options]
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url(self.question.uid),  json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_delete_on_text_type_question(self):
        self.question.update(type=QuestionTypeEnum.TEXT.value)
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url(self.question.uid),  json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 400)


class DeleteScreeningQuestionTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.url = lambda question_uid: f"screening-questions/{question_uid}"
        self.question = ScreeningQuestionFactory.create(job=self.job)

    def test_delete_question(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url(self.question.uid), headers=headers)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(ScreeningQuestion.objects.filter(uid=self.question.uid).exists())

    def test_delete_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.delete(self.url(self.question.uid), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_delete_by_talent(self):
        talent_user = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent_user.user.token}"
        }
        response = self.client.delete(self.url(self.question.uid), headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_with_invalid_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.delete(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)


class GetScreeningQuestionsTest(TestCase):
        def setUp(self):
            self.client = TestClient(router)
            self.business_user = BusinessUserFactory.create()
            self.job = JobFactory.create(created_by=self.business_user)
            self.url = lambda job_uid: f"{job_uid}/screening-questions"
            self.question = ScreeningQuestionFactory.create_batch(5, job=self.job)

        def test_get_questions(self):
            headers = {
                "authorization": f"Bearer {self.business_user.user.token}"
            }
            response = self.client.get(self.url(self.job.uid), headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()), 5)

        def test_by_another_business_user(self):
            business_user = BusinessUserFactory.create()
            headers = {
                "authorization": f"Bearer {business_user.user.token}"
            }
            response = self.client.get(self.url(self.job.uid), headers=headers)
            self.assertEqual(response.status_code, 404)


        def test_by_talent(self):
            talent_user = TalentFactory.create()
            headers = {
                "authorization": f"Bearer {talent_user.user.token}"
            }
            response = self.client.get(self.url(self.job.uid), headers=headers)
            self.assertEqual(response.status_code, 403)

        def test_by_wrong_uuid(self):
            headers = {
                "authorization": f"Bearer {self.business_user.user.token}"
            }
            response = self.client.get(self.url(uuid4()), headers=headers)
            self.assertEqual(response.status_code, 404)

class GetScreeningAnswersTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.job_post = JobPostFactory.create(job=self.job, recruiter=self.business_user)
        self.stage = WorkFlowStage.objects.filter(phase=PhaseType.NEW.value, created_by__business=self.business_user.business).first()
        self.application = JobApplicationFactory.create(job_post=self.job_post, recruiter=self.business_user, stage=self.stage)
        self.url = lambda application_id: f"applications/{application_id}/screening-answers"
        self.questions = ScreeningQuestionFactory.create_batch(5, job=self.job)
        for screening_question in self.questions:
            AnswerFactory.create(question=screening_question, application=self.application)


    def test_get_questions(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.application.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)


    def test_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.get(self.url(self.application.uid), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_by_talent(self):
        talent_user = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent_user.user.token}"
        }
        response = self.client.get(self.url(self.application.uid), headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_with_invalid_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)

class UpdateJobApplicationTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.job_post = JobPostFactory.create(job=self.job, recruiter=self.business_user)
        self.stage = WorkFlowStage.objects.filter(created_by__business=self.business_user.business).first()
        self.application = JobApplicationFactory.create(job_post=self.job_post, recruiter=self.business_user,
                                                       stage=self.stage )
        self.url = lambda application_id: f"job-posts/applications/{application_id}"


    def test_job_applications_update_forward(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        stages = WorkflowStageFactory.create_batch(3, phase=PhaseType.SCREENING.value, created_by=self.business_user)
        data = {
            "stages": [str(self.stage.uid), *list(map(lambda x:str(x.uid), stages))]
        }
        response = self.client.patch(self.url(self.application.uid), headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertIn(str(self.application.stage.uid), data["stages"][1:])

    def test_job_applications_update_backward(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        self.application.stage = WorkflowStageFactory.create(created_by=self.business_user, phase=PhaseType.INTERVIEW.value)
        self.application.save()
        self.application.refresh_from_db()
        stages = WorkflowStageFactory.create_batch(3, phase=PhaseType.SCREENING.value, created_by=self.business_user)
        data = {
            "stages": [*list(map(lambda x:str(x.uid), stages)), str(self.application.stage.uid)]
        }
        response = self.client.patch(self.url(self.application.uid), headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertIn(str(self.application.stage.uid), data["stages"][:-1])

    def test_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        stages = WorkflowStageFactory.create_batch(3, phase=PhaseType.SCREENING.value, created_by=self.business_user)
        data = {
            "stages": [str(self.stage.uid), *list(map(lambda x:str(x.uid), stages))]
        }
        response = self.client.patch(self.url(self.application.uid), headers=headers, json=data)
        self.assertEqual(response.status_code, 404)

    def test_by_talent_user(self):
        talent_user = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent_user.user.token}"
        }
        stage = WorkflowStageFactory.create_batch(3, phase=PhaseType.SCREENING.value, created_by=self.business_user)
        data = {
            "stages": [str(self.stage.uid), *list(map(lambda x:str(x.uid), stage))]
        }
        response = self.client.patch(self.url(self.application.uid), headers=headers, json=data)
        self.assertEqual(response.status_code, 403)

    def test_by_invalid_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        stage = WorkflowStageFactory.create_batch(3, phase=PhaseType.SCREENING.value, created_by=self.business_user)
        data = {
            "stages": [str(self.stage.uid), *list(map(lambda x:str(x.uid), stage))]
        }
        response = self.client.patch(self.url(uuid4()), headers=headers, json=data)
        self.assertEqual(response.status_code, 404)

class JobPostBulkUpdateTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.job = JobFactory.create(created_by=self.business_user)
        self.job_posts = JobPostFactory.create_batch(5, job=self.job, recruiter=self.business_user)
        for job_post in self.job_posts[:2]:
            JobApplicationFactory.create(job_post=job_post, recruiter=self.business_user)
        self.url = "job-posts"
        self.test_data = {
            "job_posts" : [str(job_post.uid) for job_post in self.job_posts],
            "action": ActionType.DELETE.value
        }

    def test_successful_status_update(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        self.test_data["action"] = ActionType.CLOSED.value
        response = self.client.patch(self.url, json=self.test_data, headers=headers)
        print("response: ", response.json())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobPost.objects.filter(status=ActionType.CLOSED.value).count(), 5)

    def test_successful_delete(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        self.test_data["action"] = ActionType.DELETE.value
        response = self.client.patch(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        # It didn't delete the ones with applications
        self.assertEqual(JobPost.objects.count(), 2)

    def test_by_another_business_user(self):
        business_user = BusinessUserFactory()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        self.test_data["action"] = ActionType.DELETE.value
        response = self.client.patch(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobPost.objects.count(), 5)

    def test_by_talent(self):
        talent = TalentFactory()
        headers = {
            "authorization": f"Bearer {talent.user.token}"
        }
        self.test_data["action"] = ActionType.DELETE.value
        response = self.client.patch(self.url, json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 403)


# class TalentMatchScoreTests(TestCase):
#     def setUp(self):
#         """Set up test data for talent match score tests."""
#         # Create test data
#         self.talent = TalentFactory.create()
#         self.country = Country.objects.first()
#         self.role = Role.objects.first()
#         self.job_level = JobLevel.objects.first()
#         self.education_level = EducationLevel.objects.first()
#
#         # Create job with required attributes
#         self.job = JobFactory.create(
#             role=self.role,
#             job_level=self.job_level,
#             years_of_experience=3,
#             minimum_education_level=self.education_level,
#             work_structure="remote",
#             first_language=Language.objects.first()
#         )
#         self.job.additional_languages.add(Language.objects.last())
#         self.job.save()
#
#
#
#         # Create job post
#         self.job_post = JobPostFactory.create(
#             job=self.job,
#             country=self.country
#         )
#
#         self.application = JobApplicationFactory.create(job_post=self.job_post, applicant=self.talent)
#
#         # Set up required attributes
#         self.required_attributes = RequiredAttribute.objects.filter(
#             job=self.job).first().update(
#             role=True,
#             job_level=True,
#             years_of_experience=True,
#             minimum_education_level=True,
#             work_structure=True,
#             first_language=True,
#             secondary_language=True,
#             working_hours=True,
#             location=True,
#             technological_requirement=True
#         )
#
#         # Create skills for testing
#         self.skill_category_general = SkillCategory.objects.get_or_create(name="General Skills")[0]
#         self.skill_category_tools = SkillCategory.objects.get_or_create(name="Tools/Platforms")[0]
#         self.skill_category_method = SkillCategory.objects.get_or_create(
#             name="Common Methodologies/Frameworks"
#         )[0]
#
#         self.general_skills = [
#             SkillFactory.create(name=f"General Skill {i}", category=self.skill_category_general)
#             for i in range(3)
#         ]
#         self.tool_skills = [
#             SkillFactory.create(name=f"Tool {i}", category=self.skill_category_tools)
#             for i in range(3)
#         ]
#         self.method_skills = [
#             SkillFactory.create(name=f"Method {i}", category=self.skill_category_method)
#             for i in range(3)
#         ]
#
#         # Add skills to job
#         self.job.skills.set(self.general_skills + self.tool_skills + self.method_skills)
#
#         # Create required skills
#         for skill in self.general_skills[:2]:  # First 2 general skills are required
#             RequiredSkill.objects.create(
#                 required_attribute=self.required_attributes,
#                 skill=skill
#             )
#         self.talent.skills.add(*self.general_skills[:2])
#         self.talent.save()
#
#         # Set up talent data
#         self.talent.role = self.role
#         self.talent.native_language = self.job.first_language
#         self.talent.country = self.country
#         self.talent.work_models = ["remote", "hybrid"]
#         self.talent.years_of_experience = 5
#         self.talent.technological_requirement = "yes"
#         self.talent.additional_languages.add(
#             Language.objects.last()
#         )
#
#         self.talent.save()
#
#
#         # Add education
#         EducationFactory.create(
#             talent=self.talent,
#             level=self.education_level,
#             start_date=timezone.now().date() - timedelta(days=365*5),
#             end_date=timezone.now().date() - timedelta(days=365*2),
#
#         )
#
#         # Add experience
#         ExperienceFactory.create(
#             talent=self.talent,
#             role=self.role,
#             company="Test Company",
#             start_date=timezone.now().date() - timedelta(days=365*5),
#             end_date=None,
#             level=self.job_level
#         )
#
#         # Add skills to talent (matching some job skills)
#         self.talent.skills.add(*[self.general_skills[0], self.tool_skills[1], self.method_skills[2]])
#
#         # Add available days
#         for day in [Days.MONDAY, Days.WEDNESDAY, Days.FRIDAY]:
#             TalentAvailableDay.objects.create(
#                 talent=self.talent,
#                 day=day,
#                 utc_start_time=time(9, 0),
#                 utc_end_time=time(17, 0)
#             )
#
#
#
#
#     def test_basic_match_score_calculation(self):
#         """Test basic match score calculation with all requirements met."""
#         queryset = Talent.objects.filter(id=self.talent.id)
#         queryset = add_talent_match_score(queryset, self.job_post)
#         talent = queryset.first()
#
#
#
#         print("requires_location: ", talent.requires_location)
#         print("location_score: ", talent.location_score, "\n\n")
#
#         print("requires_minimum_education: ", talent.requires_minimum_education)
#         print("has_minimum_education_requirement: ", talent.has_minimum_education_requirement, "\n\n")
#
#         print("missing_compulsory_sec_lang: ", talent.missing_compulsory_secondary_language, "\n")
#
#         print("requires_role: ", talent.requires_role)
#         print("matching_role: ", talent.matching_role, "\n\n")
#
#         print("missing_required_skill: ", talent.missing_required_skill, "\n\n")
#
#         print("requires_job_level: ", talent.requires_job_level)
#         print("has_matching_experience: ", talent.has_matching_experience, "\n\n")
#
#         print("requires_experience: ", talent.requires_experience)
#         print("meets_experience: ", talent.meets_experience, "\n\n")
#
#         print("requires_work_structure: ", talent.requires_work_structure)
#         print("work_structure_match: ", talent.work_structure_match, "\n\n")
#
#         print("requires_tech_requirement: ", talent.requires_tech_requirements)
#         print("meets_tech_requirements: ", talent.meets_tech_requirements, "\n\n")
#
#         print("missing_work_schedule: ", talent.missing_work_schedule, "\n\n")
#         print("missing_required_business_model: ", talent.missing_required_business_model)
#
#
#         print("role_score:", talent.role_score)
#         print("tools_platform_score:", talent.tools_platform_score)
#         print("methodologies_score:", talent.methodologies_score)
#         print("general_skill_score:", talent.general_skill_score)
#         print("job_level_score:", talent.job_level_score)
#         print("experience_score:", talent.experience_score)
#         print("business_model_score:", talent.business_model_score)
#         print("minimum_education_score:", talent.minimum_education_score)
#         print("work_structure_score:", talent.work_structure_score)
#         print("tech_requirement_score:", talent.tech_requirement_score)
#         print("first_language_score:", talent.first_language_score)
#         print("additional_language_score:", talent.additional_language_score)
#         print("final_work_schedule_score:", talent.final_work_schedule_score)
#         print("location_score:", talent.location_score)
#
#         print("computed_score: ", talent.computed_match_score)
#
#
#         # Individual scores should be as expected
#         self.assertEqual(talent.role_score, 6.67)
#         self.assertEqual(talent.job_level_score, 6.67)
#         self.assertEqual(talent.experience_score, 6.67)
#         self.assertEqual(talent.minimum_education_score, 6.67)
#         self.assertEqual(talent.work_structure_score, 6.67)
#         self.assertEqual(talent.first_language_score, 6.67)
#
#         # All required attributes should be met
#         # self.assertGreater(talent.computed_match_score, 80.0)
#
#     def test_basic_match_score_calculation_2(self):
#         """Test basic match score calculation with all requirements met."""
#         queryset = JobApplication.objects.filter(id=self.application.id)
#         queryset = add_application_match_score(queryset, self.job_post)
#         job_post = queryset.first()
#
#         print("requires_location: ", job_post.requires_location)
#         print("location_score: ", job_post.location_score, "\n\n")
#
#         print("requires_minimum_education: ", job_post.requires_minimum_education)
#         print("has_minimum_education_requirement: ", job_post.has_minimum_education_requirement, "\n\n")
#
#         print("missing_compulsory_sec_lang: ", job_post.missing_compulsory_secondary_language, "\n")
#
#         print("requires_role: ", job_post.requires_role)
#         print("matching_role: ", job_post.matching_role, "\n\n")
#
#         print("missing_required_skill: ", job_post.missing_required_skill, "\n\n")
#
#         print("requires_job_level: ", job_post.requires_job_level)
#         print("has_matching_experience: ", job_post.has_matching_experience, "\n\n")
#
#         print("requires_experience: ", job_post.requires_experience)
#         print("meets_experience: ", job_post.meets_experience, "\n\n")
#
#         print("requires_work_structure: ", job_post.requires_work_structure)
#
#         print("requires_tech_requirement: ", job_post.requires_tech_requirements)
#         print("meets_tech_requirements: ", job_post.meets_tech_requirements, "\n\n")
#
#         print("missing_work_schedule: ", job_post.missing_work_schedule)
#         print("missing_required_business_model: ", job_post.missing_required_business_model, "\n\n")
#
#         print("missing_required_business_model: ", job_post.missing_required_business_model, "\n\n")
#
#         print("role_score:", job_post.role_score)
#         print("tools_platform_score:", job_post.tools_platform_score)
#         print("methodologies_score:", job_post.methodologies_score)
#         print("general_skill_score:", job_post.general_skill_score)
#         print("job_level_score:", job_post.job_level_score)
#         print("experience_score:", job_post.experience_score)
#         print("business_model_score:", job_post.business_model_score)
#         print("minimum_education_score:", job_post.minimum_education_score)
#         print("work_structure_score:", job_post.work_structure_score)
#         print("tech_requirement_score:", job_post.tech_requirement_score)
#         print("first_language_score:", job_post.first_language_score)
#         print("additional_language_score:", job_post.additional_language_score)
#         print("final_work_schedule_score:", job_post.final_work_schedule_score)
#         print("location_score:", job_post.location_score)
#
#         print("computed_score: ", job_post.computed_match_score)
#
#         # Individual scores should be as expected
#         self.assertEqual(job_post.role_score, 6.67)
#         self.assertEqual(job_post.job_level_score, 6.67)
#         self.assertEqual(job_post.experience_score, 6.67)
#         self.assertEqual(job_post.minimum_education_score, 6.67)
#         self.assertEqual(job_post.work_structure_score, 6.67)
#         self.assertEqual(job_post.first_language_score, 6.67)
#
#         # All required attributes should be met
#         # self.assertGreater(job_post.computed_match_score, 80.0)
#
#     def test_missing_required_skills(self):
#         """Test score when talent is missing required skills."""
#         # Remove one required skill from talent
#         self.talent.skills.remove(self.general_skills[0])
#
#         queryset = Talent.objects.filter(id=self.talent.id)
#         queryset = add_talent_match_score(queryset, self.job_post)
#         talent = queryset.first()
#
#         # Score should be 0 because of missing required skill
#         self.assertEqual(talent.computed_match_score, 0.0)
#         self.assertTrue(talent.missing_required_skill)
#
#     def test_partial_skill_matches(self):
#         """Test score calculation with partial skill matches."""
#         # Remove required attribute to test partial scoring
#         self.required_attributes.role = False
#         self.required_attributes.job_level = False
#         self.required_attributes.years_of_experience = False
#         self.required_attributes.minimum_education_level = False
#         self.required_attributes.work_structure = False
#         self.required_attributes.first_language = False
#         self.required_attributes.working_hours = False
#         self.required_attributes.location = False
#         self.required_attributes.technological_requirement = False
#         self.required_attributes.save()
#
#         # Talent has 1 out of 2 required skills, 1/3 general skills, 1/3 tool skills, 1/3 method skills
#         queryset = Talent.objects.filter(id=self.talent.id)
#         queryset = add_talent_match_score(queryset, self.job_post)
#         talent = queryset.first()
#
#         # Calculate expected score
#         expected_score = (1/2 * 6.67) + (1/3 * 6.67) + (1/3 * 6.67) + (1/3 * 6.67)
#         expected_score = round(expected_score, 2)
#
#         self.assertAlmostEqual(talent.computed_match_score, expected_score, places=2)
#
#     def test_work_schedule_matching(self):
#         """Test work schedule matching logic."""
#         # Clear existing available days
#         TalentAvailableDay.objects.filter(talent=self.talent).delete()
#
#         # Add available days that don't match job's working hours
#         TalentAvailableDay.objects.create(
#             talent=self.talent,
#             day=Days.SUNDAY,
#             utc_start_time=time(9, 0),
#             utc_end_time=time(12, 0)
#         )
#
#         queryset = Talent.objects.filter(id=self.talent.id)
#         queryset = add_talent_match_score(queryset, self.job_post)
#         talent = queryset.first()
#         # Should have 0 work schedule score
#         self.assertEqual(talent.work_schedule_score, 0.0)
#
#         # But since working hours are not required, score shouldn't be 0
#         # self.assertGreater(talent.computed_match_score, 0.0)
#
#     def test_required_attributes(self):
#         """Test that missing required attributes result in 0 score."""
#         # Make role required
#         self.required_attributes.role = True
#         self.required_attributes.save()
#
#         # Change talent's role to not match
#         self.talent.role = Role.objects.exclude(id=self.role.id).first()
#         self.talent.save()
#
#         queryset = Talent.objects.filter(id=self.talent.id)
#         queryset = add_talent_match_score(queryset, self.job_post)
#         talent = queryset.first()
#
#         # Score should be 0 because required role doesn't match
#         self.assertEqual(talent.computed_match_score, 0.0)
#
#     def test_flexible_availability(self):
#         """Test that flexible availability is handled correctly."""
#         # Make job have flexible availability
#         self.job.flexible_availability = True
#         self.job.save()
#
#         # Clear talent's available days
#         TalentAvailableDay.objects.filter(talent=self.talent).delete()
#
#         queryset = Talent.objects.filter(id=self.talent.id)
#         queryset = add_talent_match_score(queryset, self.job_post)
#         talent = queryset.first()
#
#         # Should get full work schedule score due to flexible availability
#         self.assertEqual(talent.final_work_schedule_score, 6.67)
#
#     def test_additional_languages(self):
#         """Test additional language matching."""
#         # Add some additional languages to job
#         self.job.additional_languages.set(Language.objects.all()[:2])
#
#         # Add one matching language to talent
#         self.talent.additional_languages.set([self.job.additional_languages.first()])
#
#         # Make a language required
#         RequiredSecondaryLanguage.objects.create(
#             required_attribute=self.required_attributes,
#             language=Language.objects.first()
#         )
#
#         queryset = Talent.objects.filter(id=self.talent.id)
#         queryset = add_talent_match_score(queryset, self.job_post)
#         talent = queryset.first()
#
#         # Should have partial score for additional languages
#         self.assertEqual(talent.additional_language_score, 3.34)  # 1/2 of 6.67
#
#         # Add the required language to talent
#         self.talent.additional_languages.add(Language.objects.first())
#
#         queryset = Talent.objects.filter(id=self.talent.id)
#         queryset = add_talent_match_score(queryset, self.job_post)
#         talent = queryset.first()
#
#         # Now should have full score for required language
#         self.assertEqual(talent.additional_language_score, 6.67)
#         self.assertFalse(talent.missing_compulsory_secondary_language)
#
#     def test_compare_with_job_post_annotations(self):
#         """Test that add_talent_match_score and add_job_post_annotations produce consistent results."""
#         # First, get talent match score
#         talent_queryset = Talent.objects.filter(id=self.talent.id)
#         talent_queryset = add_talent_match_score(talent_queryset, self.job_post)
#         talent = talent_queryset.first()
#
#         # Then, get job post annotations for the same talent
#         job_post_queryset = JobPost.objects.filter(id=self.job_post.id)
#         job_post_queryset = add_job_post_annotations(job_post_queryset, self.talent)
#         job_post = job_post_queryset.first()
#
#         # Compare the computed match scores
#         self.assertAlmostEqual(
#             talent.computed_match_score,
#             job_post.computed_match_score,
#             places=2,
#             msg="Match scores should be consistent between talent and job post views"
#         )
#
#         # Compare individual score components that should match
#         score_fields = [
#             'role_score', 'job_level_score', 'experience_score',
#             'minimum_education_score', 'work_structure_score',
#             'first_language_score', 'additional_language_score'
#         ]
#
#         for field in score_fields:
#             self.assertAlmostEqual(
#                 getattr(talent, field, 0),
#                 getattr(job_post, field, 0),
#                 places=2,
#                 msg=f"{field} should be consistent between talent and job post views"
#             )
#
#         # Verify that both functions agree on required attributes
#         self.assertEqual(
#             talent.missing_required_skill,
#             job_post.missing_required_skill,
#             "Missing required skill status should match"
#         )
#
#         self.assertEqual(
#             talent.missing_compulsory_secondary_language,
#             job_post.missing_compulsory_secondary_language,
#             "Missing compulsory secondary language status should match"
#         )
#
#         # Test with a different scenario - remove a required skill
#         if talent.skills.exists():
#             skill_to_remove = talent.skills.first()
#             talent.skills.remove(skill_to_remove)
#
#             # Check both functions again
#             talent_queryset = Talent.objects.filter(id=self.talent.id)
#             talent_queryset = add_talent_match_score(talent_queryset, self.job_post)
#             talent = talent_queryset.first()
#
#             job_post_queryset = JobPost.objects.filter(id=self.job_post.id)
#             job_post_queryset = add_job_post_annotations(job_post_queryset, self.talent)
#             job_post = job_post_queryset.first()
#
#             # Both should now show a missing required skill
#             self.assertTrue(
#                 talent.missing_required_skill or job_post.missing_required_skill,
#                 "Both functions should detect missing required skill"
#             )
#
#             # If role is required and doesn't match, both should return 0 score
#             if self.required_attributes.role and talent.role != self.job.role:
#                 self.assertEqual(talent.computed_match_score, 0.0)
#                 self.assertEqual(job_post.computed_match_score, 0.0)


class JobApplicationMatchTests(TestCase):
    def setUp(self):
        self.talent: Talent = TalentFactory.create()
        self.location = Country.objects.all()[0]
        self.location2 = Country.objects.all()[1]
        self.job: Job = JobFactory.create()
        self.job_post: JobPost = JobPostFactory.create(
            job=self.job,
        )
        self.required_attributes: RequiredAttribute = self.job.requiredattribute
        self.additional_languages = Language.objects.all()[:3]
        self.additional_languages2 = self.additional_languages[:1]
        self.role = Role.objects.order_by("pk")[0]
        self.role2 = Role.objects.order_by("pk")[1]

        self.tool_platform_skills = Skill.objects.filter(category__name="Tools/Platforms")[:3]
        self.methodology_skills = Skill.objects.filter(category__name="Common Methodologies/Frameworks")[:3]
        self.general_skills = Skill.objects.filter(category__name="General Skills")[:3]

        self.level1 = JobLevel.objects.all()[0]
        self.level2 = JobLevel.objects.all()[1]

        self.job_application = JobApplicationFactory.create(
            applicant=self.talent,
            job_post=self.job_post
        )
    
    def test_role(self):
        self.update_required_attributes(role=False)
        self.job.role = self.role
        experience: Experience = ExperienceFactory.create(
            talent=self.talent,
            role=self.role2
        )
        self.talent.role = self.role2
        self.talent.save()
        self.job.save()

        queryset = JobApplication.objects.filter(id=self.job_application.id)
        queryset = add_application_match_score(queryset, self.job_post)
        job_post = queryset.first()

        role_score = Decimal(job_post.role_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(role_score, Decimal("0.0"))

        self.update_required_attributes(role=True)
        queryset = JobApplication.objects.filter(id=self.job_application.id)
        queryset = add_application_match_score(queryset, self.job_post)
        job_post = queryset.first()

        computed_match_score = Decimal(job_post.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(computed_match_score, Decimal("0.0"))

        experience.role =self.job.role
        experience.save()

        queryset = JobApplication.objects.filter(id=self.job_application.id)
        queryset = add_application_match_score(queryset, self.job_post)
        job_post = queryset.first()

        role_score = Decimal(job_post.role_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(role_score, Decimal("6.67"))
    
    def test_location(self):
        self.talent.country = self.location
        self.job_post.country = self.location
        self.update_required_attributes(location=True)
        self.talent.save()
        self.job_post.save()

        queryset = JobApplication.objects.filter(id=self.job_application.id)
        queryset = add_application_match_score(queryset, self.job_post)

        job_application = queryset.first()
        location_score = Decimal(job_application.location_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        #test matching job location
        self.assertEqual(location_score, Decimal("6.67"))

        self.talent.country = self.location2
        self.talent.save()

        queryset = JobApplication.objects.filter(id=self.job_application.id)
        queryset = add_application_match_score(queryset, self.job_post)

        job_application = queryset.first()
        location_score = Decimal(job_application.location_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        #test non matching location
        self.assertEqual(location_score, Decimal("0.0"))
    
    def test_additional_language(self):
        self.job.additional_languages.add(*self.additional_languages)
        self.talent.additional_languages.add(*self.additional_languages2)
        self.talent.save()
        self.job_post.save()

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()

        additional_language_score = Decimal(job_application.additional_language_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(additional_language_score, Decimal("2.22"))

        #add compulsory language
        RequiredSecondaryLanguage.objects.create(
            required_attribute=self.required_attributes,
            language=self.additional_languages[2]
        )

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()

        computed_match_score = Decimal(job_application.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(computed_match_score, Decimal("0.0"))
    
    def test_skills(self):
        self.update_required_attributes()
        self.job.skills.add(*self.tool_platform_skills[:0], *self.general_skills[:0], *self.methodology_skills[:0])
        self.talent.skills.all().delete()
        #self.talent.skills.add(*self.tool_platform_skills[:1], *self.general_skills[:2], *self.methodology_skills)

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()

        tool_platform_score = Decimal(job_application.tools_platform_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        methodologies_score = Decimal(job_application.methodologies_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        general_skill_score = Decimal(job_application.general_skill_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(tool_platform_score, Decimal("6.67"))
        self.assertEqual(methodologies_score, Decimal("6.67"))
        self.assertEqual(general_skill_score, Decimal("6.67"))
    
    def test_missing_required_skill_returns_zero_score(self):
        self.update_required_attributes()
        self.job.skills.add(*self.tool_platform_skills, *self.general_skills, *self.methodology_skills)
        RequiredSkill.objects.create(
            skill=self.job.skills.first(),
            required_attribute=self.required_attributes,
        )
        self.talent.skills.all().delete()
        self.talent.skills.add(*self.tool_platform_skills[:1], *self.general_skills[:2], *self.methodology_skills)
        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        tool_platform_score = Decimal(job_application.tools_platform_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        methodologies_score = Decimal(job_application.methodologies_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        general_skill_score = Decimal(job_application.general_skill_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(tool_platform_score, Decimal("2.22"))
        self.assertEqual(methodologies_score, Decimal("6.67"))
        self.assertEqual(general_skill_score, Decimal("4.45"))
    
    def test_job_level_no_score(self):
        self.update_required_attributes()
        Experience.objects.filter(talent=self.talent).delete()
        
        ExperienceFactory.create(talent=self.talent, level=self.level1)
        self.job.job_level = self.level2
        self.job.save()

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        job_level_score = Decimal(job_application.job_level_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(job_level_score, Decimal("0.0"))
    
    def test_job_level_full_score(self):
        self.update_required_attributes()
        Experience.objects.filter(talent=self.talent).delete()
        level1 = JobLevel.objects.all()[0]
        ExperienceFactory.create(talent=self.talent, level=level1)
        self.job.job_level = level1
        self.job.save()

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        job_level_score = Decimal(job_application.job_level_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(job_level_score, Decimal("6.67"))

    def test_job_level_required_or_no_score(self):
        self.update_required_attributes(job_level=True)
        Experience.objects.filter(talent=self.talent).delete()
        level1 = JobLevel.objects.all()[0]
        level2 = JobLevel.objects.all()[1]
        ExperienceFactory.create(talent=self.talent, level=level1)
        self.job.job_level = level2
        self.job.save()

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        computed_match_score = Decimal(job_application.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.assertEqual(computed_match_score, Decimal("0.0"))
    
    def test_experience_score_full(self):
        self.update_required_attributes()
        self.talent.years_of_experience = 6
        self.job.years_of_experience = 5
        self.talent.save()
        self.job.save() 

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        experience_score = Decimal(job_application.experience_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(experience_score, Decimal("6.67"))
    
    def test_experience_score_zero(self):
        self.update_required_attributes()
        self.talent.years_of_experience = 6
        self.job.years_of_experience = 8
        self.talent.save()
        self.job.save() 

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        experience_score = Decimal(job_application.experience_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(experience_score, Decimal("0.0"))
    
    def test_working_hours_complete_match_full_score(self):
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        final_work_schedule_score = Decimal(job_application.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_working_hours_incomplete_match_partial_score(self):
        self.job.flexible_availability = False
        self.talent.flexible_availability = False
        self.job.save()
        self.talent.save()
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
            AvailableDay(
                job=self.job_post.job,
                day=Days.TUESDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        final_work_schedule_score = Decimal(job_application.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("3.33"))
    
    def test_working_hours_no_job_hours_full_score(self):
        available_days = []
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        final_work_schedule_score = Decimal(job_application.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_working_hours_flexible_talent_full_score(self):
        self.talent.flexible_availability = True
        self.talent.save()
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
            AvailableDay(
                job=self.job_post.job,
                day=Days.TUESDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        talent_available_days = []
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        final_work_schedule_score = Decimal(job_application.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_working_hours_flexible_job_full_score(self):
        self.talent.flexible_availability = True
        self.job.flexible_availability = True
        self.talent.save()
        available_days = []
        talent_available_days = []
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        final_work_schedule_score = Decimal(job_application.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def test_working_hours_required_incomplete_match_zero_computed_score(self):
        self.update_required_attributes(working_hours=True)
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
            AvailableDay(
                job=self.job_post.job,
                day=Days.TUESDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(4, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        computed_match_score = Decimal(job_application.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(computed_match_score, Decimal("0.00"))
    
    def test_working_hours_match_accross_timezones(self):
        self.job.availability_timezone = "America/Los_Angeles"
        self.talent.availability_timezone = "America/New_York" #3hrs ahead
        self.talent.save()
        self.job.save()
        available_days = [
            AvailableDay(
                job=self.job_post.job,
                day=Days.MONDAY.value,
                start_time=time(8, 0),
                end_time=time(10, 0)
            ),
        ]
        talent_available_days = [
            TalentAvailableDay(
                talent=self.talent,
                day=Days.MONDAY.value,
                start_time=time(11, 0),
                end_time=time(13, 0)
            ),
        ]
        TalentAvailableDay.objects.bulk_create(talent_available_days)
        AvailableDay.objects.bulk_create(available_days)

        queryset = self.get_queryset()
        queryset = add_application_match_score(queryset, self.job_post)
        job_application = queryset.first()
        final_work_schedule_score = Decimal(job_application.final_work_schedule_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(final_work_schedule_score, Decimal("6.67"))
    
    def update_required_attributes(self, *args, **kwargs):
        for field_name in self.job.required_attributes_keys:
            if hasattr(self.required_attributes, field_name):
                field = getattr(self.required_attributes, field_name)
                if isinstance(field, models.BooleanField):
                    setattr(self.required_attributes, field, False)
        for field_name in kwargs:
            setattr(self.required_attributes, field_name, kwargs[field_name])
        self.required_attributes.save()
    
    def get_queryset(self):
        return JobApplication.objects.filter(id=self.job_application.id)


class JobPostTagAPITests(TestCase):
    def setUp(self):
        super().setUp()
        self.client = TestClient(router)
        self.url =  "jobposts/tags"
        user = UserFactory()
        business = BusinessFactory(created_by=user)
        self.business_user = BusinessUserFactory(business=business, user=user)
        job = JobFactory(created_by=self.business_user)
        self.job_post = JobPostFactory(job=job)
        j1 = JobPostTag.objects.create(business=business, name="test1")
        j2 = JobPostTag.objects.create(business=business, name="test2")
        j3 = JobPostTag.objects.create(business=business, name="test3")
        self.job_post.tags.add(j1, j2, j3)
        self.job_post.save()


    def test_get_tags(self):
        response = self.client.get(self.url, headers={"Authorization": f"Bearer {self.business_user.user.token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)


    def test_delete_tags(self):
        self.assertEqual(self.job_post.tags.count(), 3)
        response = self.client.delete(self.url, headers={"Authorization": f"Bearer {self.business_user.user.token}"},
                                      json=["test1", "test2"])
        self.assertEqual(response.status_code, 204)
        self.assertEqual(JobPostTag.objects.count(), 1)
        self.assertEqual(self.job_post.tags.count(), 1)



