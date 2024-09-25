from django.test import TestCase
from ninja.testing import TestClient
from jobs.models import (
    Job, AvailableDay, JobPost, ScreeningQuestion, QuestionOption, Language, EmploymentType, JobLevel
    )
from accounts.models import Department, Role, Business, Industry, BusinessUser, Skill, User
from ninja_jwt.authentication import JWTAuth
from jobs.business_views import router


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
        self.recruiter = User.objects.create_user(
            first_name="Recruiter",
            last_name ="Recruiter",
            email="testuser@example.com",
            password="securepassword",
        )
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
        self.auth = JWTAuth()
        self.client = TestClient(router)
        self.headers = {
            "authorization": f"bearer {self.user.token}"
        }

    def test_create_job(self):
        data = {
            "title": "EcoTech Manager",
            "employment_type_uid":str(self.employment_type.uid),
            "availability": [
                {
                    "day": "Monday",
                    "start_time": "08:23:54.706000",
                    "end_time": "08:23:54.706000"
                },
                {
                    "day": "Tuesday",
                    "start_time": "08:23:54.706000",
                    "end_time": "08:23:54.706000"
                }
              ],
            "hiring_company_name": None,
            "hiring_company_description":"EcoTech Solutions is a pioneering company in the field of sustainable technology, dedicated to developing innovative products and services that promote environmental responsibility and reduce the carbon footprint of individuals and businesses. Founded in 2010, EcoTech Solutions has grown from a small startup into a global leader in green technology, with a mission to make sustainability accessible and affordable for everyone",
            "work_structure":"remote",
            "technological_requirements": "macbook",
            "first_language_uid": str(self.language.uid),
            "additional_languages": [
                  str(self.language.uid)
            ],
            "lunch_break": "paid",
            "office_address": "string",
            "additional_hours_min": 0,
            "additional_hours_max": 0,
            "job_posts": [
                {
                "country_code": "NG",
                "province": "Delta State",
                "postal_code": "500000"
                },
                {
                "country_code": "NG",
                "province": "Rivers State",
                "postal_code": "500000"
                }
              ],
            "recruiter_uid": str(self.recruiter.uid),
            "annual_salary_min": 0,
            "annual_salary_max": 0,
            "annual_salary_currency": "string",
            "annual_bonus_min": 0,
            "annual_bonus_max": 0,
            "annual_bonus_currency": "string",
            "same_recruiter": True,
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
              "share_compensation": True,
              "department_uid": str(self.department.uid),
              "role_uid": str(self.role.uid),
              "skills": [
                  str(skill.uid) for skill in self.skills
              ],
              "job_level_uid": str(self.job_level.uid)
          }
        response = self.client.post("create", json=data, headers=self.headers)

        #Assert the job was created correctly
        job = Job.objects.filter(created_by=self.user).first()
     
        self.assertEqual(job.created_by, self.user)
        self.assertEqual(job.business, self.business)
        self.assertEqual(job.first_language, self.language)
        self.assertEqual(job.department, self.department)
        self.assertEqual(job.employment_type, self.employment_type)
        self.assertEqual(job.role, self.role)
        self.assertEqual(job.job_level, self.job_level)
        self.assertEqual(job.recruiter, self.recruiter)
     
        #Check availability
        available_days = AvailableDay.objects.filter(job=job)
        self.assertEqual(available_days.count(), 2)
     
        #Check job posts
        job_posts = JobPost.objects.filter(job=job)
        self.assertEqual(job_posts.count(), 2)
        self.assertEqual(job_posts[0].country.code, 'NG')
     
        #Check screening questions
        screening_questions = ScreeningQuestion.objects.filter(job=job)
        self.assertEqual(screening_questions.count(), 1)
        self.assertEqual(screening_questions[0].text, 'Are you eligible to work in the US?')
        self.assertFalse(screening_questions[0].is_knockout)
    
        #Check question options
        question_options = QuestionOption.objects.filter(question=screening_questions[0])
        self.assertEqual(question_options.count(), 2)
        self.assertEqual(job.skills.count(), 5)
