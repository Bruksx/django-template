import logging
import uuid

from accounts.models import Department, Role, Business, Industry, BusinessUser, Skill, User, Country, Talent
from django.test import TestCase
from factories import BusinessFactory, BusinessUserFactory, TalentFactory, JobPostFactory, RequiredAttributeFactory, \
    JobFactory, JobApplicationFactory, WorkflowStageFactory
from jobs.business_views import router
from jobs.enums import JobStatusType, PhaseType
from jobs.models import (
    Job, AvailableDay, JobPost, ScreeningQuestion, QuestionOption, Language, EmploymentType, JobLevel, JobApplication
)
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth


class JobCreationTest(TestCase):

    def setUp(self):
        # Set up necessary data for the test
        self.skills = Skill.objects.all()[:5]
        self.language = Language.objects.create(name='English')
        self.employment_type = EmploymentType.objects.create(name='Full-time')
        industry = Industry.objects.create(name="Health")
        self.department = Department.objects.create(name='IT', industry=industry)
        self.role = Role.objects.create(name='Developer', department=self.department)
        self.job_level = JobLevel.objects.create(name='Junior')
        self.user = User.objects.create_user(
            first_name="Test",
            last_name ="User",
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
            last_name ="Recruiter",
            email="testuser@example.com",
            password="securepassword",
        )
        self.recruiter_business_user = BusinessUser.objects.create(
            user=self.recruiter, 
            business=self.business,
        )
        self.auth = JWTAuth()
        self.client = TestClient(router)
        self.headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.country1 = Country.objects.order_by("?").first()
        self.country2 = Country.objects.order_by("?").first()

    # def test_create_job(self):
    #     data = {
    #         "title": "EcoTech Manager",
    #         "employment_type_uid":str(self.employment_type.uid),
    #         "availability": [
    #             {
    #                 "day": "Monday",
    #                 "start_time": "08:23:54.706000",
    #                 "end_time": "08:23:54.706000"
    #             },
    #             {
    #                 "day": "Tuesday",
    #                 "start_time": "08:23:54.706000",
    #                 "end_time": "08:23:54.706000"
    #             }
    #           ],
    #         "hiring_company_name": None,
    #         "hiring_company_description":"EcoTech Solutions is a pioneering company in the field of sustainable technology, dedicated to developing innovative products and services that promote environmental responsibility and reduce the carbon footprint of individuals and businesses. Founded in 2010, EcoTech Solutions has grown from a small startup into a global leader in green technology, with a mission to make sustainability accessible and affordable for everyone",
    #         "work_structure":"remote",
    #         "technological_requirements": "macbook",
    #         "first_language_uid": str(self.language.uid),
    #         "additional_languages": [
    #               str(self.language.uid)
    #         ],
    #         "lunch_break": "paid",
    #         "office_address": "string",
    #         "additional_hours_min": 0,
    #         "additional_hours_max": 0,
    #         "job_posts": [
    #             {
    #             "country_uid": str(self.country1.uid),
    #             "province": "Delta State",
    #             "postal_code": "500000"
    #             },
    #             {
    #             "country_uid": str(self.country2.uid),
    #             "province": "Rivers State",
    #             "postal_code": "500000"
    #             }
    #           ],
    #         "recruiter_uid": str(self.recruiter_business_user.uid),
    #         "annual_salary_min": 0,
    #         "annual_salary_max": 0,
    #         "annual_salary_currency": "string",
    #         "annual_bonus_min": 0,
    #         "annual_bonus_max": 0,
    #         "annual_bonus_currency": "string",
    #         "same_recruiter": True,
    #         "screening_questions": [
    #             {
    #             "type": "single select",
    #             "options": [
    #                 {
    #                 "is_accepted": True,
    #                 "text": "yes"
    #                 },
    #                 {
    #                 "is_accepted": False,
    #                 "text": "No"
    #                 }
    #             ],
    #             "text": "Are you eligible to work in the US?"
    #             },
    #           ],
    #           "share_compensation": True,
    #           "department_uid": str(self.department.uid),
    #           "role_uid": str(self.role.uid),
    #           "skills": [
    #               str(skill.uid) for skill in self.skills
    #           ],
    #           "job_level_uid": str(self.job_level.uid)
    #       }
    #     response = self.client.post("", json=data, headers=self.headers)
    #
    #     #Assert the job was created correctly
    #     self.assertEqual(response.status_code, 200)
    #     job = Job.objects.filter(created_by=self.business_user).first()
    #
    #     self.assertEqual(job.created_by, self.business_user)
    #     self.assertEqual(job.first_language, self.language)
    #     self.assertEqual(job.department, self.department)
    #     self.assertEqual(job.employment_type, self.employment_type)
    #     self.assertEqual(job.role, self.role)
    #     self.assertEqual(job.job_level, self.job_level)
    #     self.assertEqual(job.recruiter, self.recruiter_business_user)
    #
    #     #Check availability
    #     available_days = AvailableDay.objects.filter(job=job)
    #     self.assertEqual(available_days.count(), 2)
    #
    #     #Check job posts
    #     job_posts = JobPost.objects.filter(job=job)
    #     self.assertEqual(job_posts.count(), 2)
    #     self.assertEqual(job_posts[0].country.code, self.country1.code)
    #
    #     #Check screening questions
    #     screening_questions = ScreeningQuestion.objects.filter(job=job)
    #     self.assertEqual(screening_questions.count(), 1)
    #     self.assertEqual(screening_questions[0].text, 'Are you eligible to work in the US?')
    #     self.assertFalse(screening_questions[0].is_knockout)
    #
    #     #Check question options
    #     question_options = QuestionOption.objects.filter(question=screening_questions[0])
    #     self.assertEqual(question_options.count(), 2)
    #     self.assertEqual(job.skills.count(), 5)

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
        self.assertGreater(len(data), 3)

    def test_skill_category_list_with_search(self):
        response = self.client.get(f"{self.url}?search=test")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 3)


class TestTalentsByJobList(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        country = Country.objects.first()
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(user=self.business.created_by, business=self.business)
        self.job_post = JobPostFactory.create(country=country, recruiter=self.business_user)
        RequiredAttributeFactory.create(job=self.job_post.job)
        TalentFactory.create_batch(10, country=country)


    def test_talents_by_job_list_endpoint(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"/job-posts/{self.job_post.uid}/talents", headers=headers)
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 10)

    def test_wrong_job_post_uid(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"/job-posts/{uuid.uuid4()}/talents", headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_endpoint_call_by_talent(self):
        talent = Talent.objects.first()
        headers = {
            "authorization": f"bearer {talent.user.token}"
        }
        response = self.client.get(f"/job-posts/{self.job_post.uid}/talents", headers=headers)
        self.assertEqual(response.status_code, 403)


    def test_talents_by_job_list_endpoint_with_search(self):
        search = Talent.objects.first().user.first_name
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"/job-posts/{self.job_post.uid}/talents?search={search}", headers=headers)
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(data), 1)

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
        RequiredAttributeFactory.create(job=self.job_post.job)

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
        self.business = BusinessFactory.create()
        self.url = ""
        self.business_user = BusinessUserFactory.create(user=self.business.created_by, business=self.business)
        jobs = JobFactory.create_batch(5, created_by=self.business_user)
        for job in jobs:
            JobPostFactory.create_batch(5, country=country, job=job, recruiter=self.business_user)
            RequiredAttributeFactory.create(job=job)


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
        job = Job.objects.first()
        job.update(status=status)
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
        RequiredAttributeFactory.create(job=self.job)



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
        JobApplicationFactory.create_batch(10, job_post=self.job_post, recruiter=self.business_user)

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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

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
        stage = WorkflowStageFactory.create(phase=phase)
        application = JobApplication.objects.first()
        application.update(stage=stage)
        response = self.client.get(f"{self.url(self.job_post.uid)}?phase={phase}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_endpoint_with_new_application_query(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"{self.url(self.job_post.uid)}?new_application=true", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        application = JobApplication.objects.first()
        application.update(stage=None)
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

    def test_endpoint_with_search_query(self):
        search = Talent.objects.last().user.first_name
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(f"{self.url(self.job_post.uid)}?search={search}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertLess(response.data["count"], 10)
        self.assertGreaterEqual(response.data["count"], 1)
