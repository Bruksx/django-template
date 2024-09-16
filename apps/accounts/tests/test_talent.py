import logging

from django.template.defaultfilters import first

from accounts.enums import PreferredCommunicationType, GenderType, NoticePeriodType
from accounts.models import User, VerificationCode, Country, Talent, TalentAvailability, EducationLevel, Industry, \
    Skill, Department, SkillCategory, TalentSkill, Experience, Education
from django.test import TestCase
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth
from accounts.views import router
from core.models import Language, Currency
from jobs.models import JobLevel, EmploymentType


class ValidateOtpTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/validate-otp"
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
            "country_id": self.country.id,
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
        self.assertEqual(user.talent.country_id, self.user_data["country_id"])
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
            "availability": {
                "monday": True,
                "monday_start_time": "09:30:00",
                "monday_end_time": "06:30:00",
                "tuesday": True,
                "tuesday_start_time": "09:30:00",
                "tuesday_end_time": "06:30:00",
                "wednesday": True,
                "wednesday_start_time": "09:30:00",
                "wednesday_end_time": "06:30:00",
                "thursday": True,
                "thursday_start_time": "09:30:00",
                "thursday_end_time": "06:30:00",
                "friday": True,
                "friday_start_time": "09:30:00",
                "friday_end_time": "06:30:00",
                "saturday": False,
                "saturday_start_time": None,
                "saturday_end_time": None,
                "sunday": False,
                "sunday_start_time": None,
                "sunday_end_time": None
            },
            "bio": "I am a Tech Freak",
            "photo": None,
            "notice_period": 1,
            "notice_period_type": NoticePeriodType.WEEKS.value,
            "instagram": "https://instagram.com",
            "linkedin": "https://linkedin.com",
            "facebook": "https://facebook.com",
            "twitter_x": "https://twitterx.com"
        }
        headers = {
            "authorization": f"bearer {token}"
        }
        return data, client.post("/complete-profile/first_step", json=data, headers=headers)

    @classmethod
    def send_complete_profile_2(cls, client, token, industry):
        education_level = EducationLevel.objects.create(industry=industry, level="TestLevel")
        language = Language.objects.create(name="TestLanguage1")
        language2 = Language.objects.create(name="TestLanguage2")
        language3 = Language.objects.create(name="TestLanguage3")
        data = {
            "education_history": [
                {
                    "level_id": education_level.id,
                    "start_date": "2020-09-14",
                    "end_date": "2023-09-14",
                    "major": "Business",
                    "university": "University of Nigeria"
                }
            ],
            "cv": None,
            "native_language_id": language.id,
            "additional_languages": [
                language2.id, language3.id
            ]
        }
        headers = {
            "authorization": f"bearer {token}"
        }
        return data, client.post("/complete-profile/next_step", json=data, headers=headers)

    @classmethod
    def send_complete_profile_3(cls, client, token, industry):
        department = Department.objects.create(industry=industry,
                                               name="TestDepartment")
        skills = []
        skill_categories = []
        for category in ["tool", "framework", "bm", "general", "soft"]:
            skill_categories.append(SkillCategory.objects.create(name=f"{category.title()}Category"))
            skills.append(Skill.objects.create(name=f"{category.upper()}Skill", category=skill_categories[-1],
                                               department=department))
        job_level = JobLevel.objects.create(name="TestJobLevel")
        employment_type = EmploymentType.objects.create(name="TestEmploymentType")
        currency = Currency.objects.create(name="Naira", abbreviation="NGN")
        data = {
            "skill": {
                "additional_skills": [
                    "Skipping", "Jumping"
                ],
                "tools": [
                    skills[0].id
                ],
                "frameworks": [
                    skills[1].id
                ],
                "business_models": [
                    skills[2].id
                ],
                "general_skills": [
                    skills[3].id
                ],
                "soft_skills": [
                    skills[4].id
                ]
            },
            "experience_history": [
                {
                    "company": "Google",
                    "annual_salary": 5000,
                    "annual_salary_currency_id": currency.id,
                    "annual_salary_bonus": 500,
                    "annual_salary_bonus_currency_id": currency.id,
                    "level_id": job_level.id,
                    "employment_type_id": employment_type.id,
                    "start_date": "2020-09-14",
                    "end_date": "2023-09-14",
                    "currently_works_here": True
                }
            ]
        }
        headers = {
            "authorization": f"bearer {token}"
        }
        return data, client.post("/complete-profile/last_step", json=data, headers=headers)

    def test_complete_profile_success(self):
        self.assertIsNone(getattr(self.talent, "talentavailability", None))
        data, response = self.send_complete_profile_1(client=self.client, token=self.user.token)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.user.gender, data["gender"])
        self.assertEqual(self.talent.bio, data["bio"])
        self.assertIsNotNone(getattr(self.talent, "talentavailability", None))
        self.assertEqual(self.talent.talentavailability.friday, data["availability"]["friday"])
        self.assertEqual(self.talent.talentavailability.sunday, data["availability"]["sunday"])
        self.assertEqual(self.talent.profile_completion_stage, 1)


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
        self.assertEqual(self.talent.profile_completion_stage, 2)



    def test_complete_profile_3_success(self):
        self.assertFalse(hasattr(self.talent, "talentskill"))
        data, response = self.send_complete_profile_3(client=self.client, token=self.user.token, industry=self.industry)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.experience_set.count(), 1)
        self.assertTrue(hasattr(self.talent, "talentskill"))
        self.assertEqual(self.talent.talentskill.tools.first().id, data["skill"]["tools"][0])
        self.assertEqual(self.talent.talentskill.frameworks.first().id, data["skill"]["frameworks"][0])
        self.assertEqual(self.talent.talentskill.business_models.first().id, data["skill"]["business_models"][0])
        self.assertEqual(self.talent.talentskill.general_skills.first().id, data["skill"]["general_skills"][0])
        self.assertEqual(self.talent.talentskill.soft_skills.first().id, data["skill"]["soft_skills"][0])
        self.assertTrue(self.talent.experience_set.filter(level_id=data["experience_history"][0]["level_id"],
                                                          employment_type_id=data["experience_history"][0]["employment_type_id"]).exists())


class GetTalentProfileTests(TestCase):
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


    def test_get_talent_profile(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/talent-profile", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_after_profile_completion(self):
        CompleteProfileTests.send_complete_profile_1(client=self.client, token=self.user.token)
        CompleteProfileTests.send_complete_profile_2(client=self.client, token=self.user.token,
                                                     industry=self.industry)
        CompleteProfileTests.send_complete_profile_3(client=self.client, token=self.user.token,
                                                     industry=self.industry)
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/talent-profile", headers=headers)
        logging.critical(response.content)
