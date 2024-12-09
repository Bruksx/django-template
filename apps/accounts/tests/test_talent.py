from datetime import timezone, date
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from accounts.enums import PreferredCommunicationType, GenderType, NoticePeriodType, Days, BusinessUserRoleType
from accounts.models import User, VerificationCode, Country, Talent, EducationLevel, Industry, \
    Skill, Department, SkillCategory, Role, Business, BusinessUser, Experience, TalentAvailableDay
from accounts.views.talent import router
from chats.models import Conversation, Message
from core.models import Language, Currency
from factories import WorkflowStageFactory, TalentFactory, BusinessUserFactory
from jobs.enums import LunchBreakEnum, WorkStructureEnum, PhaseType, JobStatusType
from jobs.models import JobLevel, EmploymentType, BusinessModel, Job, JobPost, RequiredAttribute, AvailableDay, \
    JobApplication, JobInterview


class CreateAccountTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/initiate-account-creation"
        self.country =  Country.objects.create(name="Nigeria", code="NG")
        self.user_data = {
            "email": "test@example.com"
        }

    def test_email_verification_endpoint(self):
        response = self.client.post(self.url, json=self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(VerificationCode.objects.filter(email=self.user_data["email"]).exists())

class ValidateOtpTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/create-account"
        self.country =  Country.objects.create(name="Nigeria", code="NG")
        self.user_data = {
            "email": "test@example.com",
            "otp": "1234",
            "password": "securepassword",
            "phone_number": "08098988989",
            "first_name": "John",
            "last_name": "Doe",
            "preferred_communication": PreferredCommunicationType.WHATSAPP.value,
            "postal_code": "102109",
            "country": self.country.uid,
            "state": "Lagos",
            "city": "Mushin"
        }
        self.verification_code = VerificationCode(
            email=self.user_data["email"],
            code="1234",
        )
        self.verification_code.save()

    def test_validate_otp_success(self):
        response = self.client.post(self.url, json=self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Talent.objects.count(), 1)

        user = User.objects.get(email=self.user_data["email"])
        self.assertEqual(user.first_name, self.user_data["first_name"])
        self.assertEqual(user.last_name, self.user_data["last_name"])
        self.assertTrue(user.check_password(self.user_data["password"]))
        self.assertEqual(user.phone_number, self.user_data["phone_number"])
        self.assertEqual(user.talent.country.uid, self.user_data["country"])
        self.assertEqual(user.talent.state, self.user_data["state"])
        self.assertEqual(user.talent.postal_code, self.user_data["postal_code"])

    def test_validate_otp_incorrect_otp(self):
        self.user_data["otp"] = "6543"
        response = self.client.post(self.url, json=self.user_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Talent.objects.count(), 0)


    def test_validate_otp_missing_verification_code(self):
        VerificationCode.objects.all().delete()
        response = self.client.post(self.url, json=self.user_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Talent.objects.count(), 0)


    def test_validate_otp_missing_data(self):
        incomplete_data = self.user_data.copy()
        incomplete_data.pop("otp")  # Remove the OTP to simulate missing data
        response = self.client.post(self.url, json=incomplete_data)
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Talent.objects.count(), 0)

    def test_validate_wrong_email(self):
        self.user_data["email"] = "test2@example.com"
        response = self.client.post(self.url, json=self.user_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Talent.objects.count(), 0)

class CompleteProfileTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.create(name="Nigeria", code="NG")
        self.industry = Industry.objects.create(name="TestIndustry")
        self.user = User.objects.create_user(
            first_name="Test",
            last_name ="User",
            email="testuser@example.com",
            password="securepassword",
        )
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.auth = JWTAuth()
        self.auth.authenticate = lambda r: self.user

    @classmethod
    def send_complete_profile_1(cls, client, token):
        data = {
            "gender": GenderType.NON_BINARY.value,
            "visible": True,
            "bio": "I am a Tech Freak",
            "photo": None,
            "notice_period": 1,
            "notice_period_type": NoticePeriodType.WEEKS.value,
            "instagram": "https://instagram.com",
            "linkedin": "https://linkedin.com",
            "facebook": "https://facebook.com",
            "twitter_x": "https://twitter.com",
            "availability": [
                {
                    "day": Days.MONDAY.value,
                    "start_time": "09:30:00",
                    "end_time": "06:30:00"
                },
                {
                    "day": Days.TUESDAY.value,
                    "start_time": "09:30:00",
                    "end_time": "06:30:00"
                },
                {
                    "day": Days.WEDNESDAY.value,
                    "start_time": "09:30:00",
                    "end_time": "06:30:00"
                },
                {
                    "day": Days.THURSDAY.value,
                    "start_time": "09:30:00",
                    "end_time": "06:30:00"
                },
                {
                    "day": Days.FRIDAY.value,
                    "start_time": "09:30:00",
                    "end_time": "06:30:00"
                }
            ]
        }
        headers = {
            "authorization": f"bearer {token}"
        }
        return data, client.patch("/complete-profile/first_step", json=data, headers=headers)

    @classmethod
    def send_complete_profile_2(cls, client, token, industry):
        education_level = EducationLevel.objects.create(industry=industry, level="TestLevel")
        language = Language.objects.create(name="TestLanguage1")
        language2 = Language.objects.create(name="TestLanguage2")
        language3 = Language.objects.create(name="TestLanguage3")
        data = {
            "education_history": [
                {
                    "level": education_level.uid,
                    "start_date": "2020-09-14",
                    "end_date": "2023-09-14",
                    "major": "Business",
                    "university": "University of Nigeria"
                }
            ],
            "cv": None,
            "native_language": language.uid,
            "additional_languages": [
                language2.uid, language3.uid
            ]
        }
        headers = {
            "authorization": f"bearer {token}"
        }
        return data, client.patch("/complete-profile/next_step", json=data, headers=headers)

    @classmethod
    def send_complete_profile_3(cls, client, token, industry):
        department = Department.objects.create(industry=industry,
                                               name="TestDepartment")
        skills = []
        skill_categories = []
        for category in ["tool", "framework", "general", "soft"]:
            skill_categories.append(SkillCategory.objects.create(name=f"{category.title()}Category"))
            skills.append(Skill.objects.create(name=f"{category.title()}Skill", category=skill_categories[-1],
                                               department=department))
        skill_uids = [x.uid for x in skills]
        BusinessModel.objects.bulk_create(
            [BusinessModel(**data) for data in [
                dict(name="TestBM1", description="Test BM"),
                dict(name="TestBM2", description="Test BM 2")
            ]]
        )
        business_models_uids = list(BusinessModel.objects.values_list("uid", flat=True))
        job_level = JobLevel.objects.create(name="TestJobLevel")
        employment_type = EmploymentType.objects.create(name="TestEmploymentType")
        currency = Currency.objects.create(name="Naira", abbreviation="NGN")
        role = Role.objects.create(name="Accountant", department=department)
        data = {
            "skills": skill_uids,
            "additional_skills": [
                    "Skipping", "Jumping"
                ],
            "business_models": business_models_uids,
            "experience_history": [
                {
                    "role": role.uid,
                     "company": "Google",
                    "annual_salary": 5000,
                    "annual_salary_currency": currency.uid,
                    "annual_salary_bonus": 500,
                    "annual_salary_bonus_currency": currency.uid,
                    "level": job_level.uid,
                    "employment_type": employment_type.uid,
                    "start_date": "2020-09-14",
                    "end_date": "2023-09-14",
                    "currently_works_here": True
                }
            ]
        }
        headers = {
            "authorization": f"bearer {token}"
        }
        return data, client.patch("/complete-profile/last_step", json=data, headers=headers)

    def test_complete_profile_success(self):
        self.assertEqual(self.talent.talentavailableday_set.count(), 0)
        data, response = self.send_complete_profile_1(client=self.client, token=self.user.token)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.user.gender, data["gender"])
        self.assertEqual(self.talent.bio, data["bio"])
        self.assertEqual(self.talent.talentavailableday_set.count(), 5)


    def test_complete_profile_2_success(self):
        self.assertEqual(self.talent.education_set.count(), 0)
        self.assertEqual(self.talent.additional_languages.count(), 0)
        self.assertIsNone(self.talent.native_language)
        data, response = self.send_complete_profile_2(client=self.client, token=self.user.token, industry=self.industry)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.education_set.count(), 1)
        self.assertEqual(self.talent.additional_languages.count(), 2)
        self.assertEqual(self.talent.native_language.name, "TestLanguage1")
        self.assertTrue(self.talent.additional_languages.filter(name="TestLanguage2").exists())



    def test_complete_profile_3_success(self):
        self.assertEqual(self.talent.skills.count(), 0)
        data, response = self.send_complete_profile_3(client=self.client, token=self.user.token, industry=self.industry)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.experience_set.count(), 1)
        self.assertNotEqual(self.talent.skills.count(), 0)
        self.assertNotEqual(self.talent.business_models.count(), 0)
        self.assertTrue(self.talent.experience_set.filter(level__uid=data["experience_history"][0]["level"],
                                                          employment_type__uid=data["experience_history"][0]["employment_type"]).exists())


class GetTalentProfileTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.create(name="Nigeria", code="NG")
        self.industry = Industry.objects.create(name="TestIndustry")
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


    def test_get_talent_profile(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/profile", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_after_profile_completion(self):
        CompleteProfileTests.send_complete_profile_1(client=self.client, token=self.user.token)
        CompleteProfileTests.send_complete_profile_2(client=self.client, token=self.user.token,
                                                     industry=self.industry)
        CompleteProfileTests.send_complete_profile_3(client=self.client, token=self.user.token,
                                                     industry=self.industry)
        self.talent.refresh_from_db()
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/profile", headers=headers)
        self.assertEqual(response.status_code, 200)


class UpdateTalentProfileTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.create(name="Nigeria", code="NG")
        self.industry = Industry.objects.create(name="TestIndustry")
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


    def test_talent_profile_update(self):
        country = Country.objects.create(name="Ghana", code="GH")
        data = {
              "first_name": "Micheal",
              "last_name": "Test",
              "preferred_communication": PreferredCommunicationType.EMAIL.value,
              "phone_number": "09087674473",
              "country": country.uid,
              "state": "Lagos",
              "city": "Satellite Town",
              "postal_code": "102020"
            }
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.patch("/profile", headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.talent.refresh_from_db()
        self.assertNotEqual(self.user.first_name, self.user_data["first_name"])
        self.assertNotEqual(self.user.last_name, self.user_data["last_name"])
        self.assertEqual(self.user.first_name, data["first_name"])
        self.assertEqual(self.user.last_name, data["last_name"])
        self.assertEqual(self.talent.postal_code, data["postal_code"])
        self.assertEqual(self.talent.country, country)

    def test_delete_profile_education(self):
        CompleteProfileTests.send_complete_profile_2(client=self.client, token=self.user.token,
                                                     industry=self.industry)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.education_set.count(), 1)
        education_uid = self.talent.education_set.first().uid
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.delete(f"/education/{education_uid}", headers=headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.talent.education_set.count(), 0)

    def test_delete_profile_experience(self):
        CompleteProfileTests.send_complete_profile_3(client=self.client, token=self.user.token,
                                                     industry=self.industry)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.experience_set.count(), 1)
        experience_uid = self.talent.experience_set.first().uid
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.delete(f"/experience/{experience_uid}", headers=headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.talent.experience_set.count(), 0)

    def test_talent_education_update(self):
        CompleteProfileTests.send_complete_profile_2(client=self.client, token=self.user.token,
                                                     industry=self.industry)
        education_level = EducationLevel.objects.create(industry=self.industry, level="TestLevel")
        language = Language.objects.create(name="TestLanguage1")

        self.talent.refresh_from_db()
        education = self.talent.education_set.first()
        data = {
            "education_history": [
                {
                    "uid": education.uid,
                    "level": education_level.uid,
                    "start_date": "2020-09-14",
                    "end_date": "2023-09-14",
                    "major": "Computer Science",
                    "university": "University of Nigeria, Nsukka"
                }
            ],
            "native_language": language.uid,
            "additional_languages": []
        }
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertNotEqual(education.major, data["education_history"][0]["major"])
        self.assertNotEqual(education.university, data["education_history"][0]["university"])
        self.assertNotEqual(self.talent.additional_languages.count(), 0)
        response = self.client.patch("/complete-profile/next_step", json=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        education.refresh_from_db()
        self.assertEqual(education.major, data["education_history"][0]["major"])
        self.assertEqual(education.university, data["education_history"][0]["university"])
        self.assertEqual(self.talent.additional_languages.count(), 0)

    def test_talent_availability_update(self):
        CompleteProfileTests.send_complete_profile_1(client=self.client, token=self.user.token)
        self.talent.refresh_from_db()
        data = {"availability": [
                {
                    'uid': self.talent.talentavailableday_set.filter(day=Days.TUESDAY.value).first().uid,
                    "day": Days.TUESDAY.value,
                    "start_time": "09:30:00",
                    "end_time": "06:00:00"
                },
                {
                    'uid': self.talent.talentavailableday_set.filter(day=Days.WEDNESDAY.value).first().uid,
                    'active': False,
                    "day": Days.WEDNESDAY.value,
                    "start_time": "09:30:00",
                    "end_time": "06:30:00"
                },
                {
                    'uid': self.talent.talentavailableday_set.filter(day=Days.FRIDAY.value).first().uid,
                    'active': False,
                    "day": Days.FRIDAY.value,
                    "start_time": "09:30:00",
                    "end_time": "06:30:00"
                },
                {
                    "day": Days.SATURDAY.value,
                    "start_time": "12:00:00",
                    "end_time": "07:00:00"
                },

            ]
        }
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        tuesday_availability = self.talent.talentavailableday_set.filter(day=Days.TUESDAY.value).first()
        self.assertNotEqual(str(tuesday_availability.end_time), data["availability"][0]["end_time"])
        wednesday_availability = self.talent.talentavailableday_set.filter(day=Days.WEDNESDAY.value).first()
        self.assertIsNotNone(wednesday_availability)
        saturday_availability = self.talent.talentavailableday_set.filter(day=Days.SATURDAY.value).first()
        self.assertIsNone(saturday_availability)
        response = self.client.patch("/complete-profile/first_step", json=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        tuesday_availability = self.talent.talentavailableday_set.filter(day=Days.TUESDAY.value).first()
        self.assertEqual(str(tuesday_availability.end_time), data["availability"][0]["end_time"])
        wednesday_availability = self.talent.talentavailableday_set.filter(day=Days.WEDNESDAY.value).first()
        self.assertIsNone(wednesday_availability)
        saturday_availability = self.talent.talentavailableday_set.filter(day=Days.SATURDAY.value).first()
        self.assertIsNotNone(saturday_availability)
        self.assertEqual(self.talent.talentavailableday_set.count(), 4)

    def test_talent_additional_skills_update(self):
        CompleteProfileTests.send_complete_profile_3(client=self.client, token=self.user.token,
                                                     industry=self.industry)
        self.talent.refresh_from_db()
        data = {
            "additional_skills": [
                    "Skipping", "Swimming", "Baking"
                ]
        }
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertEqual(self.talent.additionalskill_set.count(), 2)
        self.assertTrue(self.talent.additionalskill_set.filter(name="Jumping").exists())
        response = self.client.patch("/complete-profile/last_step", json=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.additionalskill_set.count(), 3)
        self.assertFalse(self.talent.additionalskill_set.filter(name="Jumping").exists())
        self.assertTrue(self.talent.additionalskill_set.filter(name="Baking").exists())
        self.assertTrue(self.talent.additionalskill_set.filter(name="Skipping").exists())


class TalentDashboardTests(TestCase):
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
        self.user = User.objects.create_user(**self.user_data)
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        stage = WorkflowStageFactory.create(phase=PhaseType.INTERVIEW.value)
        self.auth = JWTAuth()
        self.auth.authenticate = lambda r: self.user
        self.department = Department.objects.first()
        self.role = Role.objects.first()
        self.currency = Currency.objects.first()
        self.job_level = JobLevel.objects.first()
        self.employment_type = EmploymentType.objects.first()
        self.education_level = EducationLevel.objects.first()
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
            industry="Technology"
        )
        self.business_user = BusinessUser.objects.create(
            user=self.user,
            business=self.business,
            role=BusinessUserRoleType.OWNER.value

        )
        self.talent.skills.set(Skill.objects.all()[:3])
        Experience.objects.create(
            talent=self.talent,
            role=self.role,
            company="TestCompany",
            annual_salary=700,
            annual_salary_currency=self.currency,
            annual_salary_bonus=700,
            annual_salary_bonus_currency=self.currency,
            level=self.job_level,
            employment_type=self.employment_type,
            start_date=date(year=2022, month=1, day=1),
            end_date=date(year=2024, month=1, day=1),
            currently_works_here=False
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
        self.job_required_attrs = RequiredAttribute.objects.create(
            job=job,
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
        self.job_required_attrs.skills.set(Skill.objects.all()[:2])
        self.job_required_attrs.business_model.set(BusinessModel.objects.all()[:2])
        self.job_required_attrs.refresh_from_db()
        TalentAvailableDay.objects.create(
            talent=self.talent,
            day=Days.WEDNESDAY,
            start_time="10:00:00",
            end_time="16:00:00"
        )
        TalentAvailableDay.objects.create(
            talent=self.talent,
            day=Days.MONDAY,
            start_time="10:00:00",
            end_time="16:00:00"
        )

        AvailableDay.objects.create(
            job=job,
            day=Days.MONDAY,
            start_time="10:00:00",
            end_time="16:00:00"
        )

        application = JobApplication.objects.create(
            job_post=self.job_post,
            applicant=self.talent,
            stage=stage,
            match=5
        )
        JobInterview.objects.create(
            application=application
        )
        conversation = Conversation.objects.create()
        conversation.users.set([self.user2, self.user])
        conversation.refresh_from_db()
        Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            job_post=self.job_post,
            body="Hello"

        )

    def test_dashboard_report_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/dashboard-report", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("jobs_applied", data)
        self.assertEqual(data["jobs_applied"], 1)
        response = self.client.get("/dashboard-report?start_date=2022-02-02&end_date=2022-09-02", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("jobs_applied", data)
        self.assertEqual(data["jobs_applied"], 0)


    def test_applications_chart_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/applications-chart", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, list))
        self.assertTrue(len(data), 12)

    def test_interviews_chart_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/interviews-chart", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, list))
        self.assertTrue(len(data), 12)


class ChangeTalentPasswordTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(
            email="kx5GQ@example.com",
            password="testpassword",
            is_active=True,
            email_verified=True
        )
        self.talent = Talent.objects.create(user=self.user)

    def test_change_password_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.patch("change-password", json={"old_password": "testpassword", "new_password": "newtestpassword"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newtestpassword"))


    def test_wrong_old_password(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.patch("change-password", json={"old_password": "wrongpassword", "new_password": "newtestpassword"}, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.user.check_password("newtestpassword"))
        self.assertTrue(self.user.check_password("testpassword"))



class TalentDetailTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = lambda talent_uid: f"{talent_uid}"
        self.talent  = TalentFactory.create()
        self.business_user = BusinessUserFactory.create()

    def test_talent_detail_endpoint(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(self.talent.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["uid"], str(self.talent.uid))

    def test_talent_detail_by_talent(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url(self.talent.uid), headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_wrong_uid(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        response = self.client.get(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)
