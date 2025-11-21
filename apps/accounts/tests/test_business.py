from urllib.parse import urlencode
from uuid import uuid4

from django.test import TestCase
import jwt
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from accounts.enums import BusinessUserRoleType, BusinessUserStatusType, BusinessSize
from accounts.models import User, VerificationCode, Business, BusinessUser, BusinessIndustry, Country, TalentFilter
from accounts.views.business import router
from factories import BusinessFactory, BusinessUserFactory, CountryFactory, CurrencyFactory, JobFactory, JobPostFactory, \
    TalentFactory, ConversationFactory, MessageFactory, JobApplicationFactory, JobApplicationWithdrawalFactory, \
    WorkflowStageFactory, UserFactory, RoleFactory, IndustryFactory, LanguageFactory, EducationLevelFactory, SkillFactory, \
    TalentFilterFactory
from jobs.enums import PhaseType, JobStatusType, WorkStructureEnum
from jobs.models import JobApplication
from settings.models import WorkFlowStage


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
        business_user  = BusinessUser.objects.last()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Business.objects.count(), 1)
        self.assertEqual(BusinessUser.objects.count(), 1)

        user = User.objects.get(email=self.user_data["email"])
        self.assertEqual(user.first_name, self.user_data["first_name"])
        self.assertEqual(user.last_name, self.user_data["last_name"])
        self.assertTrue(user.check_password(self.user_data["password"]))
        self.assertEqual(WorkFlowStage.objects.filter(created_by=business_user).count(), 3)

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
        self.industry = BusinessIndustry.objects.first()
        self.country = Country.objects.first()
        self.auth = JWTAuth()
        self.auth.authenticate = lambda r: self.user

    def test_complete_company_profile_success(self):

        data = {
            "size": BusinessSize.SIZE_251_1000.value,
            "description": "string",
            "website": "string",
            "industry_uid": str(self.industry.uid),
            "location": "string",
            "instagram": "www.instagram.com",
            "linkedin": "www.linkedin.com",
            "facebook": "www.fb.com",
            "twitter_x": "www.x.com",
            "country_uid": str(self.country.uid)
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
            "size": BusinessSize.SIZE_251_1000.value,
            "description": "string",
            "website": "string",
            "industry_uid": str(self.industry.uid),
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
        self.dashboard_keys = [
            "hires",
            "open_roles",
            "applicants",
            "avg_days_to_hire",
            "invitations_sent",
            "hires_last_3_months",
            "recruiter_performance",
            "applicant_gender",
            "hires_location",
            "stage_timelines",
            "withdrawal_reasons",
            "applicants_years_of_experience",
            "talents_by_phase",
            "talents_by_stage",
            "uid"
        ]
        business = BusinessFactory.create()
        recruiters = BusinessUserFactory.create_batch(size=self.max_data, business=business)
        job_post_list = []
        country = CountryFactory.create()
        jobs = JobFactory.create_batch(
            size=self.max_data,
            created_by=recruiters[0]
        )
        index = 0
        for job in jobs:
            job.created_by = recruiters[0]
            job.save()
            job_post_list.append(JobPostFactory.create(recruiter=recruiters[index],
                                                       status=JobStatusType.POSTED.value,
                                                       country=country,
                                                       job=job))
            index += 1

        talents = TalentFactory.create_batch(size=self.max_data)
        self.hired_stage = WorkflowStageFactory.create(phase=PhaseType.HIRED.value)
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
                application.update(stage=self.hired_stage)

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
        response = self.client.get("dashboard", headers=headers)
        for key in self.dashboard_keys:
            self.assertIn(key, response.json()["data"])
        self.assertEqual(response.status_code, 200)

    def test_dashboard_by_business_staff_with_filters(self):
        headers = {
            "authorization": f"bearer {self.staff.user.token}"
        }
        job_application = JobApplication.objects.filter(
            stage__phase=PhaseType.HIRED.value
        ).last()
        job = job_application.job_post.job

        filters = {
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",
            "role": job.role.uid,
            "client": job.hiring_company_name
        }
        query = "/dashboard?" + urlencode(filters)
        response = self.client.get(query, headers=headers)
        for key in self.dashboard_keys:
            self.assertIn(key, response.json()["data"])

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
        self.industry = BusinessIndustry.objects.first()
        self.url = ""

    def test_update_business_detail(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        data = {
            "password": "TestPassword",
            "name": "Test Company",
            "description": "Good company",
            "industry_uid": str(self.industry.uid),
        }
        self.assertNotEqual(self.business.name, data["name"])
        self.assertNotEqual(self.business.description, data["description"])
        response = self.client.patch(self.url, json=data,  headers=headers)
        self.assertEqual(response.status_code, 200)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, data["name"])
        self.assertEqual(self.business.description, data["description"])
        self.assertEqual(self.business.industry, self.industry)

    def test_data_without_password(self):
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        data = {
            "name": "Test Company",
            "description": "Good company",
        }
        response = self.client.patch(self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.business.refresh_from_db()
        self.assertNotEqual(self.business.name, data["name"])
        self.assertNotEqual(self.business.description, data["description"])
        self.assertNotEqual(self.business.industry, self.industry)

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
        self.assertNotEqual(self.business.industry, self.industry)

    def test_request_by_team_member(self):
        self.business_user.update(role=BusinessUserRoleType.TEAM_MEMBER.value)
        headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        data = {
            "name": "Test Company",
            "description": "Good company",
            "industry_uid": str(self.industry.uid)
        }
        response = self.client.patch(self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.business.refresh_from_db()
        self.assertNotEqual(self.business.name, data["name"])
        self.assertNotEqual(self.business.description, data["description"])
        self.assertNotEqual(self.business.industry, self.industry)


class GetBusinessDetailTest(TestCase):
    def setUp(self):
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
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



class GetBusinessUsersTest(TestCase):
    def setUp(self):
        business = BusinessFactory.create()
        owner = BusinessUserFactory.create(business=business,
               user=business.created_by, role=BusinessUserRoleType.OWNER.value)
        business_users = BusinessUserFactory.create_batch(
            size=10,
            business=business
        )
        BusinessUser.objects.exclude(id=owner.id).update(added_by=owner)
        self.user = owner.user
        self.url = "users"
        self.client = TestClient(router)


    def test_get_business_users(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 11)


    def test_get_business_users_with_search(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        email = BusinessUser.objects.first().user.email
        response = self.client.get(f"{self.url}?search={email}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)


class InviteBusinessUserTest(TestCase):
    def setUp(self):
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )
        self.url = "users"
        self.client = TestClient(router)


    def test_invite_business_user(self):
        headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "B2TbM@example.com",
            "role": BusinessUserRoleType.TEAM_MEMBER.value
        }
        response = self.client.post(self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 201)
        business_user = BusinessUser.objects.last()
        self.assertEqual(business_user.business, self.business)
        self.assertEqual(business_user.user.email, data["email"])
        self.assertEqual(business_user.user.first_name, data["first_name"])
        self.assertEqual(business_user.user.last_name, data["last_name"])
        self.assertEqual(business_user.role, data["role"])
        self.assertEqual(business_user.status, BusinessUserStatusType.PENDING.value)
        self.assertFalse(business_user.user.is_active)
        self.assertFalse(business_user.user.email_verified)

    def test_invite_business_user_with_existing_email(self):
        headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": self.business.created_by.email,
            "role": BusinessUserRoleType.TEAM_MEMBER.value
        }
        response = self.client.post(self.url, json=data, headers=headers)
        self.assertEqual(response.status_code, 400)


class ResendBusinessUserInviteTest(TestCase):
    def setUp(self):
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )
        self.url = lambda uid: f"users/{uid}/resend-invite"
        self.client = TestClient(router)
        invited_business_user = BusinessUserFactory.create(
            business=self.business
        )
        invited_business_user.status = BusinessUserStatusType.PENDING
        invited_business_user.save()
        user = invited_business_user.user
        user.is_active = False
        user.email_verified = False
        user.save()
        self.invited_business_user = invited_business_user


    def test_resend_business_user_invite(self):
        headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }
        response = self.client.post(self.url(self.invited_business_user.uid), headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_resend_business_user_invite_with_invalid_uid(self):
        headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }
        response = self.client.post(self.url(uuid4()), headers=headers)
        self.assertEqual(response.status_code, 404)


    def test_resend_business_user_invite_with_non_pending_status(self):
        headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }
        self.invited_business_user.status = BusinessUserStatusType.ACTIVE.value
        self.invited_business_user.save()
        response = self.client.post(self.url(self.invited_business_user.uid), headers=headers)
        self.assertEqual(response.status_code, 400)



class AcceptBusinessUserInviteTest(TestCase):
    def setUp(self):
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )
        self.url = "users/accept-invite"
        self.client = TestClient(router)
        invited_business_user = BusinessUserFactory.create(
            business=self.business
        )
        invited_business_user.status = BusinessUserStatusType.PENDING.value
        invited_business_user.save()
        user = invited_business_user.user
        user.is_active = False
        user.email_verified = False
        user.save()
        self.invited_business_user = invited_business_user

    def test_accept_business_user_invite(self):
        data = {
            "code": self.invited_business_user.get_invite_token(),
            "password": "TestPassword"
        }
        response = self.client.post(self.url, json=data)
        self.assertEqual(response.status_code, 200)
        self.invited_business_user.refresh_from_db()
        self.assertTrue(self.invited_business_user.user.is_active)
        self.assertTrue(self.invited_business_user.user.email_verified)
        self.assertTrue(self.invited_business_user.user.check_password(data["password"]))
        self.assertEqual(self.invited_business_user.status, BusinessUserStatusType.ACTIVE.value)

    def test_invalid_code(self):
        data = {
            "code": jwt.encode({"key": "fake_payload"}, "fake_private_key"),
            "password": "TestPassword"
        }
        response = self.client.post(self.url, json=data)
        self.assertEqual(response.status_code, 400)

    def test_accepted_invite(self):
        self.invited_business_user.status = BusinessUserStatusType.ACTIVE.value
        self.invited_business_user.save()
        user = self.invited_business_user.user
        user.is_active = True
        user.email_verified = True
        user.save()
        data = {
            "code": self.invited_business_user.get_invite_token(),
            "password": "TestPassword"
        }
        response = self.client.post(self.url, json=data)
        self.assertEqual(response.status_code, 400)


class DeleteBusinessUserAccountTest(TestCase):
    def setUp(self):
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )
        self.url = "users"
        self.client = TestClient(router)

    def test_delete_business_user_account(self):
        headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }
        response = self.client.delete(self.url, headers=headers)
        self.assertEqual(response.status_code, 204)
        user = User.objects.filter(id=self.business.created_by.id).first()
        self.assertIsNone(user)
        business_user = BusinessUser.objects.filter(business=self.business).first()
        self.assertIsNone(business_user)
        user = User.deleted_objects.filter(id=self.business.created_by.id).first()
        business_user = BusinessUser.deleted_objects.filter(business=self.business).first()
        self.assertIsNone(business_user)
        self.assertIsNone(user)

class UpdateBusinessUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )
        self.staff_user = UserFactory.create()
        self.business_staff = BusinessUserFactory.create(
            business = self.business,
            user=self.staff_user,
            role=BusinessUserRoleType.TEAM_MEMBER.value
        )
        self.user = self.business_user.user
        self.url = f"users/{self.business_staff.uid}/"
        self.existing_user = User.objects.create(email="existing@example.com")
        self.deleted_user = User.objects.create(email="deleted@example.com")
        self.deleted_user.delete()
        self.auth_headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }

    def test_update_business_user_success(self):
        """Successful update of a business user."""
        payload = {
            "email": "newemail@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": BusinessUserRoleType.TALENT_MANAGER.value
        }
        response = self.client.patch(self.url, json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "User updated successfully")


        # Ensure changes were applied
        self.staff_user.refresh_from_db()
        self.business_staff.refresh_from_db()
        self.business_user.refresh_from_db()
        self.assertEqual(self.staff_user.email, "newemail@example.com")
        self.assertEqual(self.staff_user.first_name, "John")
        self.assertEqual(self.business_staff.role, BusinessUserRoleType.TALENT_MANAGER.value)

    def test_update_business_user_deleted_email(self):
        """Fails if email belongs to a deleted user."""
        payload = {
            "email": "deleted@example.com",
            "role": BusinessUserRoleType.ADMIN.value,
        }
        response = self.client.patch(self.url, json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "This email is not available")

    def test_update_business_user_existing_email(self):
        """Fails if email is already in use."""
        payload = {
            "email": "existing@example.com",
            "role": BusinessUserRoleType.ADMIN.value,
        }
        response = self.client.patch(self.url, json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "This email is not available")

    def test_update_business_user_invalid_uid(self):
        """Fails when updating a non-existent user."""
        payload = {
            "email": "valid@example.com",
            "role": BusinessUserRoleType.ADMIN.value,
        }
        response = self.client.patch(f"/users/{self.deleted_user.uid}/", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)


class DeleteBusinessUserTestCase(TestCase):
    def setUp(self):
        """Set up test data."""
        self.client = TestClient(router)
        self.business = BusinessFactory.create()
        self.owner = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )
        self.owner2_user = UserFactory.create()
        self.owner2 = BusinessUserFactory.create(
            business = self.business,
            user=self.owner2_user,
            role=BusinessUserRoleType.OWNER.value
        )
        self.admin_user = UserFactory.create()
        self.team_member_user = UserFactory.create()
        self.admin = BusinessUserFactory.create(
            business = self.business,
            user=self.admin_user,
            role=BusinessUserRoleType.ADMIN.value
        )
        self.team_member = BusinessUserFactory.create(
            business = self.business,
            user=self.team_member_user,
            role=BusinessUserRoleType.TEAM_MEMBER.value
        )
        self.auth_headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }

    def test_owner_cannot_be_deleted(self):
        """Ensure an owner cannot be deleted."""
        response = self.client.delete(f"users/{self.owner2.uid}/", headers=self.auth_headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Not allowed! you cannot delete owner account")

    def test_user_cannot_delete_own_account(self):
        """Ensure a user cannot delete their own account."""
        response = self.client.delete(f"users/{self.owner.uid}/", headers=self.auth_headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Not allowed! you cannot delete your account")

    def test_admin_can_delete_team_member(self):
        """Ensure an admin can delete a team member."""
        response = self.client.delete(f"users/{self.team_member.uid}/", headers=self.auth_headers)
        self.assertEqual(response.status_code, 201)
        self.assertFalse(BusinessUser.objects.filter(uid=self.team_member.uid).exists())
        self.assertFalse(User.objects.filter(uid=self.team_member_user.uid).exists())

    def test_unauthorized_user_cannot_delete(self):
        """Ensure an unauthorized user cannot delete a business user."""
        response = self.client.delete(f"users/{self.owner.uid}/")
        self.assertEqual(response.status_code, 401)


class GetBusinessUserTestCase(TestCase):
    def setUp(self):
        """Set up test data."""
        self.client = TestClient(router)
        self.business = BusinessFactory.create()
        self.another_business = BusinessFactory.create()
        self.another_business_owner = BusinessUserFactory.create(
            business = self.another_business,
            user=self.another_business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )
        self.owner = BusinessUserFactory.create(
            business = self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )
        self.admin_user = UserFactory.create()
        self.admin = BusinessUserFactory.create(
            business = self.business,
            user=self.admin_user,
            role=BusinessUserRoleType.ADMIN.value
        )
        self.auth_headers = {
            "authorization": f"bearer {self.business.created_by.token}"
        }

    def test_owner_can_get_business_user(self):
        """Ensure an admin can retrieve a staff user's details."""
        response = self.client.get(f"users/{self.admin.uid}/", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)


    def test_owner_cannot_get_other_business_staff_user(self):
        """Ensure a staff user cannot retrieve another staff user's details."""
        auth_headers = {
            "authorization": f"bearer {self.another_business_owner.user.token}"
        }
        response = self.client.get(f"users/{self.admin.uid}/", headers=auth_headers)
        self.assertEqual(response.status_code, 404)

    def test_unauthorized_user_cannot_get_business_user(self):
        """Ensure an unauthorized user cannot retrieve a business user's details."""
        response = self.client.get(f"users/{self.admin.uid}/")
        self.assertEqual(response.status_code, 401)


class ReassignJobPostsTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)  # Use Django Ninja's TestClient
        self.business = BusinessFactory.create()

        # Create a business owner
        self.business_owner = BusinessUserFactory.create(
            business=self.business,
            user=self.business.created_by,
            role=BusinessUserRoleType.OWNER.value
        )

        # Create two recruiters
        self.recruiter1 = UserFactory.create()
        self.business_recruiter1 = BusinessUserFactory.create(
            business = self.business,
            user=self.recruiter1,
            role=BusinessUserRoleType.TEAM_MEMBER.value
        )

        self.recruiter2 = UserFactory.create()
        self.business_recruiter2 = BusinessUserFactory.create(
            business = self.business,
            user=self.recruiter2,
            role=BusinessUserRoleType.OWNER.value
        )
        self.job = JobFactory.create(
            created_by=self.business_recruiter1
        )
        self.job_post1 = JobPostFactory.create(
            job=self.job
        )
        self.job_post2 = JobPostFactory.create(
            job=self.job
        )
        self.auth_headers = {"Authorization": f"Bearer {self.business_owner.user.token}"}
        self.url = f"/users/{self.business_recruiter1.uid}/reassign-job-posts/"
        self.external_user = UserFactory.create()
        self.external_business = BusinessFactory.create()
        self.external_business_user = BusinessUserFactory.create(
            business = self.external_business,
            user=self.external_user,
            role=BusinessUserRoleType.OWNER.value
        )

    def test_successful_reassignment(self):
        """Test that job posts are reassigned successfully to another recruiter."""
        payload = {"nominee_uid": str(self.business_recruiter2.uid)}
        response = self.client.post(self.url, json=payload, headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Job posts reassigned successfully")

        # Ensure all job posts are now assigned to recruiter2
        self.job_post1.refresh_from_db()
        self.assertTrue(self.job_post1.recruiter, self.recruiter2)

    def test_unauthorized_user_cannot_reassign(self):
        """Test that an unauthorized user cannot reassign job posts."""
        unauthorized_headers = {"Authorization": f"Bearer {self.recruiter1.token}"}
        payload = {"nominee_uid": str(self.business_recruiter2.uid)}
        response = self.client.post(self.url, json=payload, headers=unauthorized_headers)
        self.assertEqual(response.status_code, 403)

    def test_invalid_nominee_uid(self):
        """Test reassigning job posts with an invalid nominee UID."""
        payload = {"nominee_uid": str(uuid4())}
        response = self.client.post(self.url, json=payload, headers=self.auth_headers)

        self.assertEqual(response.status_code, 404)

    def test_reassign_to_user_outside_business(self):
        """Test that job posts cannot be reassigned to a user outside the business."""
        payload = {"nominee_uid": str(self.external_business_user.uid)}
        response = self.client.post(self.url, json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)

    def test_missing_nominee_uid(self):
        """Test reassigning job posts with missing nominee UID in request payload."""
        response = self.client.post(self.url, json={}, headers=self.auth_headers)

        self.assertEqual(response.status_code, 422)

class UpdateTalentFilterTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.OWNER.value
        )
        tf = TalentFilterFactory.create(business_user=self.business_user)
        self.url = f"/talents-filters/{tf.uid}"
        self.headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        self.role = RoleFactory.create()
        self.industry = IndustryFactory.create()
        self.language = LanguageFactory.create()
        self.educational_level = EducationLevelFactory.create()
        self.skill = SkillFactory.create()
        self.valid_data = {
            "roles": [str(self.role.uid)],
            "industries": [str(self.industry.uid)],
            "locations": ["New York"],
            "languages": [str(self.language.uid)],
            "educational_levels": [str(self.educational_level.uid)],
            "maximum_notice_period": 30,
            "work_structure": WorkStructureEnum.REMOTE.value,
            "skills": [str(self.skill.uid)]
        }

    def test_update_talent_filter_success(self):
        response = self.client.patch(self.url, json=self.valid_data, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.business_user.refresh_from_db()
        self.assertTrue(hasattr(self.business_user, 'talentfilter'))
        self.assertEqual(list(self.business_user.talentfilter.roles.values_list('uid', flat=True)), [self.role.uid])
        self.assertEqual(list(self.business_user.talentfilter.industries.values_list('uid', flat=True)), [self.industry.uid])
        self.assertEqual(self.business_user.talentfilter.locations, ["New York"])
        self.assertEqual(list(self.business_user.talentfilter.languages.values_list('uid', flat=True)), [self.language.uid])
        self.assertEqual(list(self.business_user.talentfilter.educational_levels.values_list('uid', flat=True)), [self.educational_level.uid])
        self.assertEqual(self.business_user.talentfilter.maximum_notice_period, 30)
        self.assertEqual(self.business_user.talentfilter.work_structure, WorkStructureEnum.REMOTE.value)
        self.assertEqual(list(self.business_user.talentfilter.skills.values_list('uid', flat=True)), [self.skill.uid])

    def test_update_talent_filter_unauthorized(self):
        # Test without authentication
        response = self.client.patch(self.url, json=self.valid_data)
        self.assertEqual(response.status_code, 401)

        # Test with non-business user
        talent_user = UserFactory.create(type="TALENT")
        headers = {
            "authorization": f"bearer {talent_user.token}"
        }
        response = self.client.patch(self.url, json=self.valid_data, headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_update_talent_filter_invalid_data(self):
        invalid_data = {
            "work_structure": "INVALID_STRUCTURE",
            "maximum_notice_period": -1,
            "roles": ["invalid-uuid"],
            "industries": ["invalid-uuid"],
            "languages": ["invalid-uuid"],
            "educational_levels": ["invalid-uuid"],
            "skills": ["invalid-uuid"]
        }
        response = self.client.patch(self.url, json=invalid_data, headers=self.headers)
        self.assertEqual(response.status_code, 422)

    def test_update_talent_filter_existing_filter(self):
        # Create initial filter
        TalentFilterFactory.create(business_user=self.business_user)
        
        # Update with new values
        response = self.client.patch(self.url, json=self.valid_data, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.business_user.refresh_from_db()
        self.assertEqual(list(self.business_user.talentfilter.roles.values_list('uid', flat=True)),
                         [self.role.uid])
        self.assertEqual(list(self.business_user.talentfilter.industries.values_list('uid', flat=True)),
                         [self.industry.uid])
        self.assertEqual(list(self.business_user.talentfilter.educational_levels.values_list('uid', flat=True)),
                         [self.educational_level.uid])
        self.assertEqual(self.business_user.talentfilter.locations, ["New York"])
        self.assertEqual(list(self.business_user.talentfilter.languages.values_list('uid', flat=True)), [self.language.uid])
        self.assertEqual(self.business_user.talentfilter.maximum_notice_period, 30)
        self.assertEqual(self.business_user.talentfilter.work_structure, WorkStructureEnum.REMOTE.value)
        self.assertEqual(list(self.business_user.talentfilter.skills.values_list('uid', flat=True)), [self.skill.uid])


class GetTalentFilterTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.OWNER.value
        )
        self.headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        # Create initial talent filter with all fields
        self.role = RoleFactory.create()
        self.industry = IndustryFactory.create()
        self.language = LanguageFactory.create()
        self.educational_level = EducationLevelFactory.create()
        self.skill = SkillFactory.create()
        self.talent_filter = TalentFilterFactory.create(
            business_user=self.business_user,
            locations=["New York"],
            maximum_notice_period=30,
            work_structure=WorkStructureEnum.REMOTE.value
        )
        self.talent_filter.languages.add(self.language)
        self.talent_filter.roles.add(self.role)
        self.talent_filter.industries.add(self.industry)
        self.talent_filter.educational_levels.add(self.educational_level)
        self.talent_filter.skills.add(self.skill)
        self.talent_filter.save()
        self.url = f"/talents-filters/{self.talent_filter.uid}"

    def test_get_talent_filter_success(self):
        response = self.client.get(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["roles"][0]["uid"], str(self.role.uid))
        self.assertEqual(data["roles"][0]["name"], self.role.name)
        self.assertEqual(data["industries"][0]["uid"], str(self.industry.uid))
        self.assertEqual(data["industries"][0]["name"], self.industry.name)
        self.assertEqual(data["locations"][0], "New York")
        self.assertEqual(len(data["locations"]), 1)
        self.assertEqual(len(data["educational_levels"]), 1)
        self.assertEqual(len(data["industries"]), 1)
        self.assertEqual(len(data["roles"]), 1)
        self.assertEqual(len(data["languages"]), 1)
        self.assertEqual(data["languages"][0]["uid"], str(self.language.uid))
        self.assertEqual(data["languages"][0]["name"], self.language.name)
        self.assertEqual(data["educational_levels"][0]["uid"], str(self.educational_level.uid))
        self.assertEqual(data["educational_levels"][0]["industry"], self.educational_level.industry.name)
        self.assertEqual(data["maximum_notice_period"], 30)
        self.assertEqual(data["work_structure"], WorkStructureEnum.REMOTE.value)
        self.assertEqual(len(data["skills"]), 1)
        self.assertEqual(data["skills"][0]["uid"], str(self.skill.uid))
        self.assertEqual(data["skills"][0]["name"], self.skill.name)

    def test_get_talent_filter_unauthorized(self):
        # Test without authentication
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

        # Test with non-business user
        talent_user = UserFactory.create(type="TALENT")
        headers = {
            "authorization": f"bearer {talent_user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_get_talent_filter_not_found(self):
        # Delete the talent filter
        self.talent_filter.hard_delete()
        response = self.client.get(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 404)


    def test_get_talent_filter_different_business(self):
        # Create another business user
        other_business = BusinessFactory.create()
        other_business_user = BusinessUserFactory.create(
            business=other_business,
            role=BusinessUserRoleType.OWNER.value
        )
        headers = {
            "authorization": f"bearer {other_business_user.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 404)


class DeleteTalentFilterTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.OWNER.value
        )
        self.headers = {
            "authorization": f"bearer {self.business_user.user.token}"
        }
        # Create initial talent filter with all fields
        self.role = RoleFactory.create()
        self.industry = IndustryFactory.create()
        self.language = LanguageFactory.create()
        self.educational_level = EducationLevelFactory.create()
        self.skill = SkillFactory.create()
        self.talent_filter = TalentFilterFactory.create(
            business_user=self.business_user,
            locations=["New York"],
            maximum_notice_period=30,
            work_structure=WorkStructureEnum.REMOTE.value
        )
        self.talent_filter.languages.add(self.language)
        self.talent_filter.roles.add(self.role)
        self.talent_filter.industries.add(self.industry)
        self.talent_filter.educational_levels.add(self.educational_level)
        self.talent_filter.skills.add(self.skill)
        self.talent_filter.save()
        self.url = f"/talents-filters/{self.talent_filter.uid}"

    def test_get_talent_filter_success(self):
        response = self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(TalentFilter.objects.filter(uid=self.talent_filter.uid).exists())

    def test_delete_talent_filter_unauthorized(self):
        # Test without authentication
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 401)

        # Test with non-business user
        talent_user = UserFactory.create(type="TALENT")
        headers = {
            "authorization": f"bearer {talent_user.token}"
        }
        response = self.client.delete(self.url, headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_delete_talent_filter_not_found(self):
        # Delete the talent filter
        self.talent_filter.hard_delete()
        response = self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 404)


    def test_delete_talent_filter_different_business(self):
        # Create another business user
        other_business = BusinessFactory.create()
        other_business_user = BusinessUserFactory.create(
            business=other_business,
            role=BusinessUserRoleType.OWNER.value
        )
        headers = {
            "authorization": f"bearer {other_business_user.user.token}"
        }
        response = self.client.delete(self.url, headers=headers)
        self.assertEqual(response.status_code, 404)


class TransferBusinessUserRoleTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/users/transfer-role"
        
        # Create a business with an owner
        self.business = BusinessFactory.create()
        self.owner = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.OWNER.value
        )
        
        # Create two business users to transfer role between
        self.from_user = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.ADMIN.value
        )
        self.to_user = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.TEAM_MEMBER.value
        )
        
        # Set up authentication headers
        self.headers = {
            "authorization": f"bearer {self.owner.user.token}"
        }
        
        # Create payload for role transfer
        self.payload = {
            "from_business_user": str(self.from_user.uid),
            "to_business_user": str(self.to_user.uid)
        }
    
    def test_transfer_role_success(self):
        """Test successful role transfer between business users"""
        response = self.client.post(self.url, json=self.payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Role transferred successfully")
        
        # Refresh users from database
        self.from_user.refresh_from_db()
        self.to_user.refresh_from_db()
        
        # Verify role was transferred
        self.assertEqual(self.to_user.role, BusinessUserRoleType.ADMIN.value)
    
    def test_transfer_role_unauthorized(self):
        """Test role transfer without authentication"""
        response = self.client.post(self.url, json=self.payload)
        self.assertEqual(response.status_code, 401)
        
        # Verify roles were not changed
        self.from_user.refresh_from_db()
        self.to_user.refresh_from_db()
        self.assertEqual(self.from_user.role, BusinessUserRoleType.ADMIN.value)
        self.assertEqual(self.to_user.role, BusinessUserRoleType.TEAM_MEMBER.value)
    
    def test_transfer_role_not_owner_or_admin(self):
        """Test role transfer by a regular member (not owner or admin)"""
        # Create a regular member
        member = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.TEAM_MEMBER.value
        )
        
        # Set up authentication headers for the member
        member_headers = {
            "authorization": f"bearer {member.user.token}"
        }
        
        response = self.client.post(self.url, json=self.payload, headers=member_headers)
        self.assertEqual(response.status_code, 403)
        
        # Verify roles were not changed
        self.from_user.refresh_from_db()
        self.to_user.refresh_from_db()
        self.assertEqual(self.from_user.role, BusinessUserRoleType.ADMIN.value)
        self.assertEqual(self.to_user.role, BusinessUserRoleType.TEAM_MEMBER.value)
    
    def test_transfer_role_from_user_not_found(self):
        """Test role transfer with non-existent from_user"""
        invalid_payload = {
            "from_business_user": str(uuid4()),
            "to_business_user": str(self.to_user.uid)
        }
        
        response = self.client.post(self.url, json=invalid_payload, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Previous Assignee not found")
        
        # Verify roles were not changed
        self.from_user.refresh_from_db()
        self.to_user.refresh_from_db()
        self.assertEqual(self.from_user.role, BusinessUserRoleType.ADMIN.value)
        self.assertEqual(self.to_user.role, BusinessUserRoleType.TEAM_MEMBER.value)
    
    def test_transfer_role_to_user_not_found(self):
        """Test role transfer with non-existent to_user"""
        invalid_payload = {
            "from_business_user": str(self.from_user.uid),
            "to_business_user": str(uuid4())
        }
        
        response = self.client.post(self.url, json=invalid_payload, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "New Assignee not found")
        
        # Verify roles were not changed
        self.from_user.refresh_from_db()
        self.to_user.refresh_from_db()
        self.assertEqual(self.from_user.role, BusinessUserRoleType.ADMIN.value)
        self.assertEqual(self.to_user.role, BusinessUserRoleType.TEAM_MEMBER.value)
    
    def test_transfer_role_different_business(self):
        """Test role transfer between users from different businesses"""
        # Create another business and user
        other_business = BusinessFactory.create()
        other_user = BusinessUserFactory.create(
            business=other_business,
            role=BusinessUserRoleType.ADMIN.value
        )
        
        # Try to transfer role from user in another business
        invalid_payload = {
            "from_business_user": str(other_user.uid),
            "to_business_user": str(self.to_user.uid)
        }
        
        response = self.client.post(self.url, json=invalid_payload, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        
        # Verify roles were not changed
        self.from_user.refresh_from_db()
        self.to_user.refresh_from_db()
        other_user.refresh_from_db()
        self.assertEqual(self.from_user.role, BusinessUserRoleType.ADMIN.value)
        self.assertEqual(self.to_user.role, BusinessUserRoleType.TEAM_MEMBER.value)
        self.assertEqual(other_user.role, BusinessUserRoleType.ADMIN.value)