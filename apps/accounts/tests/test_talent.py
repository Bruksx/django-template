from datetime import timezone, date, time
from decimal import Decimal
from uuid import uuid4

from database_seeder import generate_data
from django.test import TestCase
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from accounts.enums import Days, BusinessUserRoleType
from accounts.models import User, VerificationCode, Country, Talent, EducationLevel, Industry, \
    Skill, Department, Role, Business, BusinessUser, Experience, TalentAvailableDay, BusinessIndustry
from accounts.views.talent import router
from chats.models import Conversation, Message
from core.models import Currency
from factories import WorkflowStageFactory, TalentFactory, BusinessUserFactory, CountryFactory, IndustryFactory, \
    LanguageFactory, EducationFactory, EducationLevelFactory, RoleFactory, ExperienceFactory, SkillFactory, \
    BusinessModelFactory, CurrencyFactory, JobLevelFactory, EmploymentTypeFactory
from jobs.enums import LunchBreakEnum, PhaseType, JobStatusType
from jobs.models import JobLevel, EmploymentType, BusinessModel, Job, JobPost, AvailableDay, \
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
            "password": "Securepassword1*",
            "phone_number": "08098988989",
            "first_name": "John",
            "last_name": "Doe"
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

class GetTalentProfileTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.talent = TalentFactory.create()


    def test_get_talent_profile(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get("/profile", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_by_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.get("/profile", headers=headers)
        self.assertEqual(response.status_code, 403)



class UpdateTalentProfileTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "profile"
        self.country = CountryFactory.create()
        self.industry = IndustryFactory.create()
        self.talent = TalentFactory.create()
        self.native_language = LanguageFactory.create()
        self.additional_languages = LanguageFactory.create_batch(3)
        self.education_history = EducationFactory.create(talent=self.talent)
        self.level = EducationLevelFactory.create()
        self.role  = RoleFactory.create()
        self.experience_history = ExperienceFactory.create(talent=self.talent)
        self.skills = SkillFactory.create_batch(3)
        self.business_models = BusinessModelFactory.create_batch(3)
        self.currency = CurrencyFactory.create()
        self.job_level = JobLevelFactory.create()
        self.employment_type = EmploymentTypeFactory.create()

        self.data = {
          "first_name": "John",
          "last_name": "Doe",
          "preferred_communication": "text",
          "phone_number": "+15551234567",
          "country": str(self.country.uid),
          "state": "California",
          "city": "Los Angeles",
          "postal_code": "90001",
          "whatsapp_number": "+15559876543",
          "viber_number": "",
          "address": "123 Main St",
          "gender": "male",
          "visible": True,
          "bio": "I am a highly motivated and results-oriented professional with [Number] years of experience in [Industry]. I am passionate about [Area of expertise] and eager to contribute to a dynamic and challenging work environment.",
          "notice_period": 0,
          "notice_period_type": "days",
          "instagram": "johndoe_official",
          "linkedin": "john-doe-123",
          "facebook": "john.doe.123",
          "twitter_x": "johndoe",
          "native_language": str(self.native_language.uid),
          "additional_languages": [str(language.uid) for language in self.additional_languages],
          "education_history": [
            {
              "uid": str(self.education_history.uid),
              "level": str(self.level.uid),
              "start_date": "2020-01-01",
              "end_date": "2024-05-31",
              "major": "Computer Science",
              "university": "University of California, Los Angeles"
            }
          ],
          "experience_history": [
            {
              "role": str(self.role.uid),
              "uid": str(self.experience_history.uid),
              "annual_salary_bonus_currency": str(self.currency.uid),
              "annual_salary_currency": str(self.currency.uid),
              "employment_type": str(self.employment_type.uid),
              "level": str(self.job_level.uid),
              "company": "Acme Corporation",
              "annual_salary": 120000,
              "annual_salary_bonus": 15000,
              "start_date": "2022-01-15",
              "end_date": "2024-12-31",
              "currently_works_here": False
            }
          ],
          "availability": [
            {
              "active": True,
              "day": "Monday",
              "end_time": "17:00:00Z",
              "start_time": "09:00:00Z"
            }
          ],
          "skills": [str(skill.uid) for skill in self.skills],
          "additional_skills": [
            "Python", "JavaScript", "React", "SQL", "Agile"
          ],
          "business_models": [str(business_model.uid) for business_model in self.business_models]
        }

    def test_talent_profile_update(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.patch(
            path=self.url,
            json=self.data,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.user.first_name, "John")
        self.assertEqual(self.talent.user.last_name, "Doe")
        self.assertEqual(self.talent.preferred_communication, "text")
        self.assertEqual(self.talent.user.phone_number, "+15551234567")
        self.assertEqual(self.talent.country, self.country)
        self.assertEqual(self.talent.state, "California")
        self.assertEqual(self.talent.city, "Los Angeles")
        self.assertEqual(self.talent.postal_code, "90001")
        self.assertEqual(self.talent.whatsapp_number, "+15559876543")
        self.assertEqual(self.talent.viber_number, "")
        self.assertEqual(self.talent.address, "123 Main St")
        self.assertEqual(self.talent.user.gender, "male")
        self.assertTrue(self.talent.visible)
        self.assertEqual(self.talent.bio,
                         "I am a highly motivated and results-oriented professional with [Number] years of experience in [Industry]. I am passionate about [Area of expertise] and eager to contribute to a dynamic and challenging work environment.")
        self.assertEqual(self.talent.notice_period, 0)
        self.assertEqual(self.talent.notice_period_type, "days")
        self.assertEqual(self.talent.instagram, "johndoe_official")
        self.assertEqual(self.talent.linkedin, "john-doe-123")
        self.assertEqual(self.talent.facebook, "john.doe.123")
        self.assertEqual(self.talent.twitter_x, "johndoe")
        self.assertEqual(self.talent.native_language, self.native_language)
        self.assertTrue(self.talent.additional_languages.filter(uid__in=self.data["additional_languages"]).exists())
        # Assert education history (check all fields)
        self.assertEqual(self.talent.education_set.last().level, self.level)
        self.assertEqual(self.talent.education_set.last().start_date, date(2020, 1, 1))
        self.assertEqual(self.talent.education_set.last().end_date, date(2024, 5, 31))
        self.assertEqual(self.talent.education_set.last().major, "Computer Science")
        self.assertEqual(self.talent.education_set.last().university, "University of California, Los Angeles")
        # Assert experience history (check all fields)
        self.assertEqual(self.talent.experience_set.last().role, self.role)
        self.assertEqual(self.talent.experience_set.last().annual_salary_bonus_currency, self.currency)
        self.assertEqual(self.talent.experience_set.last().annual_salary_currency, self.currency)
        self.assertEqual(self.talent.experience_set.last().employment_type, self.employment_type)
        self.assertEqual(self.talent.experience_set.last().level, self.job_level)
        self.assertEqual(self.talent.experience_set.last().company, "Acme Corporation")
        self.assertEqual(self.talent.experience_set.last().annual_salary, 120000)
        self.assertEqual(self.talent.experience_set.last().annual_salary_bonus, 15000)
        self.assertEqual(self.talent.experience_set.last().start_date, date(2022, 1, 15))
        self.assertEqual(self.talent.experience_set.last().end_date, date(2024, 12, 31))
        self.assertFalse(self.talent.experience_set.last().currently_works_here)
        # Assert availability (check all fields)
        self.assertEqual(self.talent.talentavailableday_set.last().day, "Monday")
        self.assertEqual(self.talent.talentavailableday_set.last().start_time, time(hour=9, minute=0))
        self.assertEqual(self.talent.talentavailableday_set.last().end_time, time(hour=17, minute=0))
        # Assert skills
        self.assertTrue(self.talent.skills.filter(uid__in=self.data["skills"]).exists())
        # Assert additional skills
        self.assertListEqual(self.talent.additional_skills, self.data["additional_skills"])
        # Assert business models
        self.assertTrue(self.talent.business_models.filter(uid__in=self.data["business_models"]).exists())

    def test_partial_profile_update(self):
        self.assertTrue(self.talent.visible)
        headers = {
            "Authorization": f"Bearer {self.talent.user.token}"
        }
        employment_type = EmploymentType.objects.first().uid
        data = {
            "visible": False,
            "bio": "hello",
            "work_model": "hybrid",
            "employment_type": str(employment_type)
        }
        response = self.client.patch(path=self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertFalse(self.talent.visible)
        self.assertEqual(self.talent.bio, "hello")
        self.assertEqual(self.talent.work_model, "hybrid")
        self.assertEqual(self.talent.employment_type.uid, employment_type)
        data = {
            "visible": False,
            "bio": ""
        }
        response = self.client.patch(path=self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertFalse(self.talent.visible)
        self.assertEqual(self.talent.bio, "")


    def test_update_by_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "Authorization": f"Bearer {business_user.user.token}"
        }
        data = {
            "visible": False
        }
        response = self.client.patch(path=self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 403)


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
        self.industry = BusinessIndustry.objects.order_by("?").first()
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
            industry=self.industry
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
        job.requiredattribute.skills.set(Skill.objects.all()[:2])
        job.requiredattribute.business_models.set(BusinessModel.objects.all()[:2])
        job.requiredattribute.save()
        job.refresh_from_db()
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
        data = response.json()["data"]
        self.assertIn("jobs_applied", data)
        self.assertEqual(data["jobs_applied"], 1)
        response = self.client.get("/dashboard-report?start_date=2022-02-02&end_date=2022-09-02", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("jobs_applied", data)
        self.assertEqual(data["jobs_applied"], 0)


    def test_dashboard_chart_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/dashboard-charts", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("applications", data)
        self.assertIn("interviews", data)
        self.assertTrue(isinstance(data["applications"], list))
        self.assertTrue(isinstance(data["interviews"], list))
        self.assertTrue(len(data["applications"]), 12)
        self.assertTrue(len(data["interviews"]), 12)


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
        response = self.client.patch("change-password", json={"old_password": "testpassword",
                                                              "new_password": "Newtestpassword1*"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Newtestpassword1*"))


    def test_wrong_old_password(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.patch("change-password", json={"old_password": "wrongpassword",
                                                              "new_password": "Newtestpassword1*"}, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.user.check_password("Newtestpassword1*"))
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


class DeleteTalentUserAccountTest2(TestCase):
    def setUp(self):
        generate_data(silent=True)
        self.url = "/"
        self.client = TestClient(router)

        self.talent = Talent.objects.order_by("?").first()
        self.business_user = BusinessUser.objects.order_by("?").first()

    def test_delete_talent_user_account(self):
        from jobs.models import SavedJob #noqa
        from accounts.models import Experience, Education #noqa

        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }

        response = self.client.delete(self.url, headers=headers)
        self.assertEqual(response.status_code, 204)
        user = User.objects.filter(id=self.talent.user.id).first()
        self.assertIsNone(user)
        talent_user = Talent.objects.filter(id=self.talent.id).first()
        self.assertIsNone(talent_user)
        user = User.deleted_objects.filter(id=self.talent.user.id).first()
        talent_user = Talent.deleted_objects.filter(id=self.talent.id).first()

        self.assertFalse(SavedJob.global_objects.filter(talent=talent_user).exists())
        self.assertFalse(Education.global_objects.filter(talent=talent_user).exists())
        self.assertFalse(Experience.global_objects.filter(talent=talent_user).exists())

