import uuid
from random import choice
from uuid import uuid4
from decimal import Decimal, ROUND_HALF_UP

from accounts.models import Department, Role, Business, Industry, BusinessUser, Skill, User, Country, Talent, \
    EducationLevel, SkillCategory, Experience
from core.models import Currency
from django.test import TestCase
from django.db import models
from django.utils import timezone
from factories import BusinessFactory, BusinessUserFactory, TalentFactory, JobPostFactory, RequiredAttributeFactory, \
    JobFactory, JobApplicationFactory, WorkflowStageFactory, UserFactory, SkillFactory, BusinessModelFactory, \
    CountryFactory, ScreeningQuestionFactory, AnswerFactory, CurrencyFactory, ExperienceFactory
from future.backports.datetime import timedelta
from jobs.business_views import router, job_list
from jobs.enums import JobStatusType, PhaseType, QuestionTypeEnum, ActionType
from jobs.models import (
    Job, AvailableDay, JobPost, ScreeningQuestion, QuestionOption, Language, EmploymentType, JobLevel, JobApplication,
    BusinessModel, RequiredSkill, RequiredAttribute
)
from jobs.queries import add_application_match_score
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from settings.models import WorkFlowStage


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
            "responsibilities": [
                "Create innovative solutions to address environmental challenges",
                "Collaborate with cross-functional teams to design and implement sustainable solutions"
            ],
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
                    "province": "Delta State",
                    "postal_code": "500000",
                    "share_compensation": True,
                    "status": JobStatusType.POSTED.value,
                    "benefits": [
                        "Health Insurance",
                        "Dental Insurance"
                    ],

                    "annual_salary_min": 100,
                    "annual_salary_max": 1000,
                    "annual_salary_currency": str(self.currency1.uid),
                    "annual_bonus_min": 100,
                    "annual_bonus_max": 150,
                    "recruiter": str(self.business_user.uid),
                    "annual_bonus_currency": str(self.currency1.uid)

                },
                {
                    "country": str(self.country2.uid),
                    "province": "Rivers State",
                    "postal_code": "500000",
                    "share_compensation": False,
                    "benefits": [
                        "Health Insurance",
                        "Dental Insurance"
                    ],
                    "annual_salary_min": 200,
                    "annual_salary_max": 400,
                    "annual_salary_currency": str(self.currency2.uid),
                    "annual_bonus_min": 100,
                    "annual_bonus_max": 150,
                    "annual_bonus_currency": str(self.currency2.uid),
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
            "responsibilities": [
                "Create innovative solutions to address environmental challenges",
                "Collaborate with cross-functional teams to design and implement sustainable solutions"
            ],
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
                    "status": JobStatusType.DRAFT.value,
                    "annual_salary_currency": str(self.currency.uid),
                    "annual_bonus_currency": str(self.currency.uid),
                    "annual_salary_min": 100,
                    "annual_salary_max": 1000,
                    "annual_bonus_min": 200,
                    "annual_bonus_max": 2000
                }
            ],
            "additional_hours_start": "12:00:00",
            "additional_hours_end": "22:00:00",
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
        self.assertEqual(job_post.benefits, self.test_data["job_posts"][0]["benefits"])
        self.assertEqual(job_post.status, self.test_data["job_posts"][0]["status"])
        self.assertEqual(str(job_post.annual_salary_currency.uid), self.test_data["job_posts"][0]["annual_salary_currency"])
        self.assertEqual(str(job_post.annual_bonus_currency.uid), self.test_data["job_posts"][0]["annual_bonus_currency"])
        self.assertEqual(job_post.annual_salary_min, self.test_data["job_posts"][0]["annual_salary_min"])
        self.assertEqual(job_post.annual_salary_max, self.test_data["job_posts"][0]["annual_salary_max"])
        self.assertEqual(job_post.annual_bonus_min, self.test_data["job_posts"][0]["annual_bonus_min"])
        self.assertEqual(job_post.annual_bonus_max, self.test_data["job_posts"][0]["annual_bonus_max"])

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
                "annual_salary_currency": str(self.currency.uid),
                "annual_bonus_currency": str(self.currency.uid),
                "annual_salary_min": 100,
                "annual_salary_max": 1000,
                "annual_bonus_min": 3000,
                "annual_bonus_max": 4000
            },
            {
                "uid": self.job_posts[1].uid,
                "benefits": [
                    "Holiday",
                    "Paid time off"
                ],
                "country": str(self.job_posts[0].country.uid),
                "annual_salary_currency": str(self.currency.uid),
                "annual_bonus_currency": str(self.currency.uid),
                "annual_salary_min": 100,
                "annual_salary_max": 1000,
                "annual_bonus_min": 200,
                "annual_bonus_max": 2000
            },
            {
                "benefits": [
                    "Holiday",
                    "Paid time off"
                ],
                "country": str(self.country.uid),
                "annual_salary_currency": str(self.currency.uid),
                "annual_bonus_currency": str(self.currency.uid),
                "annual_salary_min": 500,
                "annual_salary_max": 1000,
                "annual_bonus_min": 200,
                "annual_bonus_max": 5000
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
        self.assertEqual(str(job_post.annual_salary_currency.uid), self.test_data["job_posts"][0]["annual_salary_currency"])
        self.assertEqual(str(job_post.annual_bonus_currency.uid), self.test_data["job_posts"][0]["annual_bonus_currency"])
        self.assertEqual(job_post.annual_salary_min, self.test_data["job_posts"][0]["annual_salary_min"])
        self.assertEqual(job_post.annual_salary_max, self.test_data["job_posts"][0]["annual_salary_max"])
        self.assertEqual(job_post.annual_bonus_min, self.test_data["job_posts"][0]["annual_bonus_min"])
        self.assertEqual(job_post.annual_bonus_max, self.test_data["job_posts"][0]["annual_bonus_max"])

        job_post = self.job_posts[1]
        job_post.refresh_from_db()
        self.assertEqual(job_post.benefits, self.test_data["job_posts"][1]["benefits"])
        self.assertEqual(str(job_post.country.uid), self.test_data["job_posts"][1]["country"])
        self.assertEqual(str(job_post.annual_salary_currency.uid), self.test_data["job_posts"][1]["annual_salary_currency"])
        self.assertEqual(str(job_post.annual_bonus_currency.uid), self.test_data["job_posts"][1]["annual_bonus_currency"])
        self.assertEqual(job_post.annual_salary_min, self.test_data["job_posts"][1]["annual_salary_min"])
        self.assertEqual(job_post.annual_salary_max, self.test_data["job_posts"][1]["annual_salary_max"])
        self.assertEqual(job_post.annual_bonus_min, self.test_data["job_posts"][1]["annual_bonus_min"])
        self.assertEqual(job_post.annual_bonus_max, self.test_data["job_posts"][1]["annual_bonus_max"])


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
        self.currency = Currency.objects.first()
        self.test_data = {
                  "country": str(self.country.uid),
                  "benefits": [
                    "Holiday",
                    "Paid time off"
                  ],
                  "recruiter": str(self.business_user.uid),
                  "status": JobStatusType.POSTED.value,
                  "annual_salary_currency": str(self.currency.uid),
                  "annual_bonus_currency": str(self.currency.uid),
                  "province": "Los Angeles",
                  "postal_code": "12345",
                  "share_compensation": True,
                  "annual_salary_min": 100,
                  "annual_salary_max": 1000,
                  "annual_bonus_min": 200,
                  "annual_bonus_max": 2000
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
        self.assertEqual(job_post.annual_salary_currency, self.currency)
        self.assertEqual(job_post.annual_bonus_currency, self.currency)
        self.assertEqual(job_post.province, self.test_data["province"])
        self.assertEqual(job_post.postal_code, self.test_data["postal_code"])
        self.assertEqual(job_post.share_compensation, self.test_data["share_compensation"])
        self.assertEqual(job_post.annual_salary_min, self.test_data["annual_salary_min"])
        self.assertEqual(job_post.annual_salary_max, self.test_data["annual_salary_max"])
        self.assertEqual(job_post.annual_bonus_min, self.test_data["annual_bonus_min"])
        self.assertEqual(job_post.annual_bonus_max, self.test_data["annual_bonus_max"])

        self.assertEqual(job_post.posted_by, self.business_user)

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
        self.url = lambda job_post_uid: f"job-post/{job_post_uid}"
        self.test_data = {
            "benefits": [
                "Holiday",
                "Paid time off"
            ],
            "status": JobStatusType.DRAFT.value,
            "annual_salary_currency": str(self.currency.uid),
            "annual_bonus_currency": str(self.currency.uid),
            "annual_salary_min": 100,
            "annual_salary_max": 1000,
            "annual_bonus_min": 200,
            "annual_bonus_max": 2000
        }

    def test_update_job_post(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }

        self.assertNotEqual(self.job_post.status, self.test_data["status"])
        self.assertNotEqual(self.job_post.annual_salary_currency, self.currency.abbreviation)
        self.assertNotEqual(self.job_post.annual_bonus_currency, self.currency.abbreviation)
        self.assertNotEqual(self.job_post.annual_salary_min, self.test_data["annual_salary_min"])
        self.assertNotEqual(self.job_post.annual_salary_max, self.test_data["annual_salary_max"])
        self.assertNotEqual(self.job_post.annual_bonus_min, self.test_data["annual_bonus_min"])
        self.assertNotEqual(self.job_post.annual_bonus_max, self.test_data["annual_bonus_max"])

        response = self.client.patch(self.url(self.job_post.uid), json=self.test_data, headers=headers)
        self.assertEqual(response.status_code, 200)

        self.job_post.refresh_from_db()
        data = response.json()
        self.assertEqual(self.test_data["status"], data["status"])
        self.assertNotEqual(str(self.job_post.uid), data["uid"])
        self.assertEqual(data["benefits"], self.test_data["benefits"])
        self.assertEqual(self.job_post.status, "closed")
        self.assertEqual(data["annual_salary_currency"], self.currency.abbreviation)
        self.assertEqual(data["annual_bonus_currency"], self.currency.abbreviation)
        self.assertEqual(data["annual_salary_min"], self.test_data["annual_salary_min"])
        self.assertEqual(data["annual_salary_max"], self.test_data["annual_salary_max"])
        self.assertEqual(data["annual_bonus_min"], self.test_data["annual_bonus_min"])
        self.assertEqual(data["annual_bonus_max"], self.test_data["annual_bonus_max"])

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
        self.url = lambda job_post_uid: f"job-post/{job_post_uid}"

    def test_delete_job_post(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.delete(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 204)

        job_post = JobPost.objects.filter(uid=self.job_post.uid).first()
        self.assertIsNone(job_post)

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
        country = CountryFactory.create()
        self.business_user = BusinessUserFactory.create()
        TalentFactory.create_batch(5, country=country)
        job = JobFactory.create(created_by=self.business_user)
        job.requiredattribute.update(location=True)
        self.job_post = JobPostFactory.create(job=job, country=country)
        self.url = lambda job_post_uid: f"job-posts/{job_post_uid}/talents"


    def test_get_talents_by_job_post(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 5)

    def test_get_talents_invisibility(self):
        talent = Talent.objects.first()
        talent.update(visible=False)
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.job_post.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def test_get_talents_by_job_post_with_search_query(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        search_query = Talent.objects.first().user.first_name
        response = self.client.get(self.url(self.job_post.uid)+f"?search={search_query}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertLess(len(response.data), 5)

    def test_invalid_job_post_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_get_talents_by_job_post_by_talent(self):
        talent = Talent.objects.first()
        headers = {
            "authorization": f"Bearer {talent.user.token}"
        }
        response = self.client.get(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_get_talents_by_job_post_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        response = self.client.get(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)

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
        self.application = JobApplicationFactory.create(job_post=self.job_post, recruiter=self.business_user)
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


    def test_job_applications_update(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        stage = WorkflowStageFactory.create(phase=PhaseType.SCREENING.value)
        data = {
            "stage": str(stage.uid)
        }
        response = self.client.patch(self.url(self.application.uid), headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.stage.uid, stage.uid)


    def test_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"Bearer {business_user.user.token}"
        }
        stage = WorkflowStageFactory.create(phase=PhaseType.SCREENING.value)
        data = {
            "stage": str(stage.uid)
        }
        response = self.client.patch(self.url(self.application.uid), headers=headers, json=data)
        self.assertEqual(response.status_code, 404)

    def test_by_talent_user(self):
        talent_user = TalentFactory.create()
        headers = {
            "authorization": f"Bearer {talent_user.user.token}"
        }
        stage = WorkflowStageFactory.create(phase=PhaseType.SCREENING.value)
        data = {
            "stage": str(stage.uid)
        }
        response = self.client.patch(self.url(self.application.uid), headers=headers, json=data)
        self.assertEqual(response.status_code, 403)

    def test_by_invalid_uid(self):
        headers = {
            "authorization": f"Bearer {self.business_user.user.token}"
        }
        stage = WorkflowStageFactory.create(phase=PhaseType.SCREENING.value)
        data = {
            "stage": str(stage.uid)
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

        self.job_applicantion = JobApplication.objects.create(
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

        queryset = JobApplication.objects.filter(id=self.job_applicantion.id)
        queryset = add_application_match_score(queryset, self.job_post)
        job_post = queryset.first()

        role_score = Decimal(job_post.role_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(role_score, Decimal("0.0"))

        self.update_required_attributes(role=True)
        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_application_match_score(queryset, self.talent)
        job_post = queryset.first()

        computed_match_score = Decimal(job_post.computed_match_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(computed_match_score, Decimal("0.0"))

        experience.role =self.job.role
        experience.save()

        queryset = JobPost.objects.filter(id=self.job_post.id)
        queryset = add_application_match_score(queryset, self.talent)
        job_post = queryset.first()

        role_score = Decimal(job_post.role_score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(role_score, Decimal("6.67"))
    
    def update_required_attributes(self, *args, **kwargs):
        for field_name in self.job.required_attributes_keys:
            if hasattr(self.required_attributes, field_name):
                field = getattr(self.required_attributes, field_name)
                if isinstance(field, models.BooleanField):
                    setattr(self.required_attributes, field, False)
        for field_name in kwargs:
            setattr(self.required_attributes, field_name, kwargs[field_name])
        self.required_attributes.save()