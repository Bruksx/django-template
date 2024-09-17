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
                    skills[0].uid
                ],
                "frameworks": [
                    skills[1].uid
                ],
                "business_models": [
                    skills[2].uid
                ],
                "general_skills": [
                    skills[3].uid
                ],
                "soft_skills": [
                    skills[4].uid
                ]
            },
            "experience_history": [
                {
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
        self.assertFalse(hasattr(self.talent, "talentskill"))
        data, response = self.send_complete_profile_3(client=self.client, token=self.user.token, industry=self.industry)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.experience_set.count(), 1)
        self.assertTrue(hasattr(self.talent, "talentskill"))
        self.assertEqual(self.talent.talentskill.tools.first().uid, data["skill"]["tools"][0])
        self.assertEqual(self.talent.talentskill.frameworks.first().uid, data["skill"]["frameworks"][0])
        self.assertEqual(self.talent.talentskill.business_models.first().uid, data["skill"]["business_models"][0])
        self.assertEqual(self.talent.talentskill.general_skills.first().uid, data["skill"]["general_skills"][0])
        self.assertEqual(self.talent.talentskill.soft_skills.first().uid, data["skill"]["soft_skills"][0])
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
        response = self.client.patch("/talent-profile", headers=headers, json=data)
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
        response = self.client.delete(f"/talent/education/{education_uid}", headers=headers)
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
        response = self.client.delete(f"/talent/experience/{experience_uid}", headers=headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.talent.experience_set.count(), 0)

    def test_education_update(self):
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
        response = self.client.post("/complete-profile/next_step", json=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        education.refresh_from_db()
        self.assertEqual(education.major, data["education_history"][0]["major"])
        self.assertEqual(education.university, data["education_history"][0]["university"])
        self.assertEqual(self.talent.additional_languages.count(), 0)
