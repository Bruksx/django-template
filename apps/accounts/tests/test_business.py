import logging
from http.client import responses
from urllib.parse import urlencode

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from accounts.enums import BusinessUserRoleType
from accounts.views.business import router
from accounts.models import User, VerificationCode, Business, BusinessUser
from factories import BusinessFactory, BusinessUserFactory, CountryFactory, CurrencyFactory, JobFactory, JobPostFactory, \
    TalentFactory, ConversationFactory, MessageFactory, JobApplicationFactory, JobApplicationWithdrawalFactory
from jobs.enums import StageType, JobStatusType
from jobs.models import JobApplication


class ValidateOtpTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/create-account"
        self.user_data = {
            "email": "test@example.com",
            "otp": "1234",
            "password": "securepassword",
            "first_name": "John",
            "last_name": "Doe",
            "role": "admin",
            "company_name": "Test Company"
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
        self.assertEqual(Business.objects.count(), 1)
        self.assertEqual(BusinessUser.objects.count(), 1)

        user = User.objects.get(email=self.user_data["email"])
        self.assertEqual(user.first_name, self.user_data["first_name"])
        self.assertEqual(user.last_name, self.user_data["last_name"])
        self.assertTrue(user.check_password(self.user_data["password"]))

    def test_validate_otp_incorrect_otp(self):
        self.user_data["otp"] = "6543"  
        response = self.client.post(self.url, json=self.user_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Business.objects.count(), 0)
        self.assertEqual(BusinessUser.objects.count(), 0)

    def test_validate_otp_missing_verification_code(self):
        VerificationCode.objects.all().delete()
        response = self.client.post(self.url, json=self.user_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Business.objects.count(), 0)
        self.assertEqual(BusinessUser.objects.count(), 0)

    def test_validate_otp_missing_data(self):
        incomplete_data = self.user_data.copy()
        incomplete_data.pop("otp")  # Remove the OTP to simulate missing data
        response = self.client.post(self.url, json=incomplete_data)
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Business.objects.count(), 0)
        self.assertEqual(BusinessUser.objects.count(), 0)



class CompleteCompanyProfileTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email='testuser@mail.com', password='testpass')
        self.business = Business.objects.create(name="Test Business", created_by=self.user)
        self.business_user = BusinessUser.objects.create(user=self.user, business=self.business)

        self.auth = JWTAuth()
        self.auth.authenticate = lambda r: self.user

    def test_complete_company_profile_success(self):

        data = {
            "size": 10,
            "description": "string",
            "website": "string",
            "industry": "string",
            "location": "string",
            "logo": "base64string",
            "instagram": "www.instagram.com",
            "linkedin": "www.linkedin.com",
            "facebook": "www.fb.com",
            "twitter_x": "www.x.com"
        }
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.patch("/complete-company-profile", json=data, headers=headers)
        self.business.refresh_from_db()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.business.description, data["description"])

    def test_complete_company_profile_forbidden(self):
        other_user = User.objects.create_user(email='otheruser@mail.com', password='otherpass')
        data = {
            "size": 10,
            "description": "string",
            "website": "string",
            "industry": "string",
            "location": "string",
            "logo": "base64string",
            "instagram": "www.instagram.com",
            "linkedin": "www.linkedin.com",
            "facebook": "www.fb.com",
            "twitter_x": "www.x.com"
        }
        headers = {
            "authorization": f"bearer {other_user.token}"
        }
        response = self.client.patch("/complete-company-profile", json=data, headers=headers)

        self.assertEqual(response.status_code, 403)

class BusinessDashboardTestCase(TestCase):
    max_data = 3
    sub_data = 2
    def setUp(self):
        self.client = TestClient(router)

        business = BusinessFactory.create()
        recruiters = BusinessUserFactory.create_batch(size=self.max_data, business=business)
        job_post_list = []
        country = CountryFactory.create()
        currency = CurrencyFactory.create()
        jobs = JobFactory.create_batch(
            size=self.max_data,
            created_by=recruiters[0],
            annual_salary_currency=currency,
            annual_bonus_currency=currency,
            recruiter=recruiters[0]

        )
        index = 0
        for job in jobs:
            job.recruiter = recruiters[0]
            job.save()
            job_post_list.append(JobPostFactory.create(recruiter=recruiters[index],
                                                       status=JobStatusType.POSTED.value,
                                                       country=country,
                                                       job=job))
            index += 1

        talents = TalentFactory.create_batch(size=self.max_data)
        for talent in talents:
            for index in range(self.sub_data):
                conversation = ConversationFactory.create(
                    users=[recruiters[index].user, talent.user]
                )
                MessageFactory.create(
                    conversation=conversation,
                    sender=recruiters[index].user,
                    job_post=job_post_list[index]
                )

            for index in range(self.max_data):
                JobApplicationFactory.create(applicant=talent, job_post=job_post_list[index])
            for index in range(self.sub_data, self.max_data):
                application = JobApplication.objects.filter(applicant=talent, job_post=job_post_list[index]).first()
                application.update(stage=StageType.HIRED.value)

            for index in range(0, self.sub_data):
                JobApplicationWithdrawalFactory.create(job_post=job_post_list[index], talent=talent)

        self.business = business
        self.country = country
        self.talent = talents[0]
        self.staff = recruiters[0]

    def test_dashboard_by_talent(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get("dashboard", headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_dashboard_by_business_staff(self):
        headers = {
            "authorization": f"bearer {self.staff.user.token}"
        }
        dashboard_keys = [
            "hires",
            "open_roles",
            "applicants",
            "avg_days_to_hire",
            "invitations_sent",
            "hires_last_3_months",
            "recruiter_performance",
            "applicant_gender",
            "hires_location",
            "time_to_hire",
            "withdrawal_reasons",
            "applicants_years_of_experience",
            "talent_per_stage",
            "uid"
        ]
        response = self.client.get("dashboard", headers=headers)
        for key in dashboard_keys:
            self.assertIn(key, response.json())
        self.assertEqual(response.status_code, 200)

    def test_dashboard_by_business_staff_with_filters(self):
        headers = {
            "authorization": f"bearer {self.staff.user.token}"
        }
        job_application = JobApplication.objects.filter(
            stage=StageType.HIRED.value
        ).last()
        job = job_application.job_post.job

        filters = {
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",
            "role": job.role.uid,
            "client": job.hiring_company_name
        }
        query = "/dashboard?" + urlencode(filters)
        dashboard_keys = [
            "hires",
            "open_roles",
            "applicants",
            "avg_days_to_hire",
            "invitations_sent",
            "hires_last_3_months",
            "recruiter_performance",
            "applicant_gender",
            "hires_location",
            "time_to_hire",
            "withdrawal_reasons",
            "applicants_years_of_experience",
            "talent_per_stage",
            "uid"
        ]
        response = self.client.get(query, headers=headers)
        for key in dashboard_keys:
            self.assertIn(key, response.json())

        self.assertEqual(response.status_code, 200)

class UpdateBusinessDetailTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(business=self.business,
                                                        role=BusinessUserRoleType.OWNER.value)
        user = self.business_user.user
        user.set_password("TestPassword")
        user.save()
        self.url = ""

    def test_update_business_detail(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        data = {
            "password": "TestPassword",
            "name": "Test Company",
            "description": "Good company",
            "industry": "Software"
        }
        self.assertNotEqual(self.business.name, data["name"])
        self.assertNotEqual(self.business.description, data["description"])
        self.assertNotEqual(self.business.industry, data["industry"])
        response = self.client.patch(self.url, json=data,  headers=headers)
        self.assertEqual(response.status_code, 200)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, data["name"])
        self.assertEqual(self.business.description, data["description"])
        self.assertEqual(self.business.industry, data["industry"])

    def test_data_without_password(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        data = {
            "name": "Test Company",
            "description": "Good company",
            "industry": "Software"
        }
        response = self.client.patch(self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.business.refresh_from_db()
        self.assertNotEqual(self.business.name, data["name"])
        self.assertNotEqual(self.business.description, data["description"])
        self.assertNotEqual(self.business.industry, data["industry"])

    def test_data_with_incorrect_password(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        data = {
            "password": "TestPassword2",
            "name": "Test Company",
            "description": "Good company",
            "industry": "Software"
        }
        response = self.client.patch(self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.business.refresh_from_db()
        self.assertNotEqual(self.business.name, data["name"])
        self.assertNotEqual(self.business.description, data["description"])
        self.assertNotEqual(self.business.industry, data["industry"])

    def test_request_by_team_member(self):
        self.business_user.update(role=BusinessUserRoleType.TEAM_MEMBER.value)
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        data = {
            "name": "Test Company",
            "description": "Good company",
            "industry": "Software"
        }
        response = self.client.patch(self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.business.refresh_from_db()
        self.assertNotEqual(self.business.name, data["name"])
        self.assertNotEqual(self.business.description, data["description"])
        self.assertNotEqual(self.business.industry, data["industry"])


class GetBusinessDetailTest(TestCase):
    def setUp(self):
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by
        )
        self.url = ""
        self.client = TestClient(router)


    def test_business_detail_endpoint(self):
        headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        business_uid = response.json()["uid"]
        self.assertEqual(str(self.business.uid), business_uid)







