from uuid import uuid4

from django.test import TestCase
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from accounts.enums import CaseReasonType
from accounts.models import Country, Industry, User, Talent, CustomerCase, VerificationCode, TalentFilter
from accounts.views.common import router
from chats.views import ws_router
from factories import (UserFactory, TalentFactory, BusinessUserFactory, RoleFactory, IndustryFactory, LanguageFactory,
                       SkillFactory, TalentFilterFactory, EducationLevelFactory, ExperienceFactory, EducationFactory,
                       CountryFactory, DepartmentFactory)
from jobs.enums import WorkStructureEnum


class CommonListTests(TestCase):
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
        self.auth = JWTAuth()
        self.auth.authenticate = lambda r: self.user

    def test_country_list_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/countries", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_educational_level_list_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/educational-levels", headers=headers)
        self.assertEqual(response.status_code, 200)


class CustomerCaseTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(
            email="kx5GQ@example.com",
            password="testpassword",
            is_active=True,
            email_verified=True
        )
        self.talent = Talent.objects.create(user=self.user)

    def test_customer_case_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertFalse(CustomerCase.objects.filter(user=self.user).exists())

        response = self.client.post("customer-cases",
                                    json=dict(reason=CaseReasonType.SYSTEM_HELP.value,
                                            description="test description",
                                              subject="test subject",),
                                    headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomerCase.objects.filter(user=self.user).exists())

class InitiateEmailChangeTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = UserFactory.create()
        self.url = "initiate-email-change"

    def test_initiate_email_change_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "email": "testemail@example.com"
        }
        self.assertFalse(VerificationCode.objects.filter(email=body["email"]).exists())
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertTrue(VerificationCode.objects.filter(email=body["email"]).exists())
        self.assertEqual(response.status_code, 200)

    def test_with_same_email(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "email": self.user.email
        }
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 400)

    def test_with_existing_user_email(self):
        user = UserFactory.create()
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "email": user.email
        }
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 400)



class ChangeEmailTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "change-email"
        self.user = UserFactory.create()
        self.new_email = "testemail@example.com"
        self.otp = VerificationCode(email=self.new_email).save()

    def test_email_change_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "email": self.new_email,
            "otp": self.otp
        }
        self.assertNotEqual(self.user.email, body["email"])
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(VerificationCode.objects.filter(email=self.new_email).exists())
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, body["email"])

    def test_wrong_email(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "email": "testemail33@example.com",
            "otp": self.otp
        }
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 400)

    def test_incorrect_otp(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "email": self.new_email,
            "otp": f"{self.otp}7"
        }
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 400)

    def test_with_existing_user_email(self):
        UserFactory.create(email=self.new_email)
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "email": self.new_email,
            "otp": self.otp
        }
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 400)


class PasswordChangeTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "change-password"
        self.user = UserFactory.create()
        self.user.set_password("TestPassword")
        self.user.save()

    def test_password_change_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "old_password": "TestPassword",
            "new_password": "NewPassword"
        }
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(body["old_password"]))
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(body["new_password"]))

    def test_wrong_old_password(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "old_password": "WrongPassword",
            "new_password": "NewPassword"
        }
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.check_password(body["new_password"]), False)

class PhoneNumberChangeTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "change-phone-number"
        self.user = UserFactory.create(phone_number="+234123456789")
        self.user.set_password("TestPassword")
        self.user.save()

    def test_phone_number_change_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "password": "TestPassword",
            "phone_number": "+234123456789"
        }
        self.assertEqual(self.user.phone_number, body["phone_number"])
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.phone_number, body["phone_number"])

    def test_wrong_old_password(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "password": "WrongPassword",
            "phone_number": "+234123456789"
        }
        response = self.client.post(self.url, headers=headers,
                                    json=body)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.user.phone_number, body["phone_number"])


class TalentListTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "talents"
        self.talent = TalentFactory.create()
        TalentFactory.create_batch(5)
        self.business_user = BusinessUserFactory.create()
        self.headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }

    def test_talent_list_endpoint(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 6)

    def test_talent_list_with_search(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(f"{self.url}?search={self.talent.user.email}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_for_talent_invisibility(self):
        self.talent.update(visible=False)
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 5)

    def test_endpoint_by_business_user(self):
        self.talent.update(visible=False)
        response = self.client.get(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 5)

    def test_endpoint_by_business_user_with_talent_filter(self):
        # Create a talent filter for the business user
        role = RoleFactory.create()
        industry = IndustryFactory.create()
        language = LanguageFactory.create()
        educational_level = EducationLevelFactory.create()
        skill = SkillFactory.create(department=DepartmentFactory(industry=industry))
        country = CountryFactory.create(name="New York")

        talent = TalentFactory.create(user=UserFactory(first_name="John"), country=country, notice_period=5,
                                                       work_model=WorkStructureEnum.REMOTE.value,
                                                       native_language=language)
        talent2 = TalentFactory.create(user=UserFactory(first_name="Jane"), country=country, notice_period=6,
                                                        work_model=WorkStructureEnum.REMOTE.value)
        TalentFactory.create(user=UserFactory(first_name="John"), notice_period=18,
                                                        work_model=WorkStructureEnum.HYBRID.value)
        EducationFactory(level=educational_level, talent=talent)
        EducationFactory(level=educational_level, talent=talent2)

        ExperienceFactory(talent=talent, role=role)
        ExperienceFactory(talent=talent2, role=role)
        talent2.additional_languages.add(language)
        talent2.save()
        talent.skills.add(skill)
        talent.save()
        talent2.skills.add(skill)
        talent2.save()

        talent_filter = TalentFilterFactory.create(
            business_user=self.business_user,
            role=role,
            industry=industry,
            location="New York",
            educational_level=educational_level,
            maximum_notice_period=14,
            work_structure=WorkStructureEnum.REMOTE.value
        )
        talent_filter.languages.add(language)
        talent_filter.skills.add(skill)

        response = self.client.get(f"{self.url}?apply_filter=true", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)  # Only the matching talent should be returned
        self.assertEqual(data["results"][0]["uid"], str(talent.uid))


    def test_endpoint_by_business_user_with_no_matching_talents(self):
        # Create a talent filter with specific criteria
        role = RoleFactory.create()
        industry = IndustryFactory.create()

        role2 = RoleFactory.create()

        TalentFilterFactory.create(
            business_user=self.business_user,
            role=role,
            industry=industry
        )

        talent = TalentFactory.create(user=UserFactory(first_name="John"))
        talent2 = TalentFactory.create(user=UserFactory(first_name="Jane"))
        talent3 = TalentFactory.create(user=UserFactory(first_name="John"))
        # Create talents that match the filter
        ExperienceFactory.create(talent=talent, role=role2)
        ExperienceFactory.create(talent=talent2, role=role2)
        ExperienceFactory.create(
            talent=talent3,
            role=role2,
        )

        response = self.client.get(f"{self.url}?apply_filter=true", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)  # No matching talents should be returned

    def test_endpoint_by_business_user_with_talent_filter_and_search(self):
        # Create a talent filter
        role = RoleFactory.create()
        industry = IndustryFactory.create()

        role2 = RoleFactory.create()
        industry2 = IndustryFactory.create()

        skill = SkillFactory(department=DepartmentFactory(industry=industry))
        skill2= SkillFactory(department=DepartmentFactory(industry=industry2))
        
        TalentFilter.objects.create(
            business_user=self.business_user,
            role=role,
            industry=industry
        )

        talent = TalentFactory.create(user=UserFactory(first_name="John"))
        talent2 = TalentFactory.create(user=UserFactory(first_name="Jane"))
        talent3 = TalentFactory.create(user=UserFactory(first_name="John"))
        # Create talents that match the filter
        ExperienceFactory.create(talent=talent, role=role)
        ExperienceFactory.create(talent=talent2, role=role)
        ExperienceFactory.create(
            talent=talent3,
            role=role2,
        )

        talent.skills.add(skill)
        talent.save()
        talent2.skills.add(skill)
        talent2.save()
        talent3.skills.add(skill2)
        talent3.save()


        response = self.client.get(f"{self.url}?search=John&apply_filter=true", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)  # Only the matching talent with name "John" should be returned
        self.assertEqual(data["results"][0]["uid"], str(talent.uid))

class SendEmailToOTPTest(TestCase):
    def setUp(self):
        self.url = "send-email-otp"
        self.client = TestClient(router)
        self.talent = TalentFactory.create()
        self.data = {
            "email": self.talent.user.email
        }

    def test_send_otp_to_email(self):
        self.assertIsNone(VerificationCode.objects.filter(email=self.data["email"]).first())
        response = self.client.post(
            self.url, json=self.data
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(VerificationCode.objects.filter(email=self.data["email"]).first())

    def test_non_existent_email(self):
        self.data["email"] = f"s{self.data['email']}"
        response = self.client.post(
            self.url, json=self.data
        )
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(VerificationCode.objects.filter(email=self.data["email"]).first())
