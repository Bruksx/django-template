from datetime import timezone as dt_timezone, datetime, date
from uuid import uuid4

from accounts.enums import BusinessUserRoleType, BusinessUserStatusType, UserType
from accounts.models import Business, BusinessIndustry, BusinessUser, User, Talent, BannedAccount, AdminUserInvite
from accounts.views.admin import router
from core.models import PageMetric, APIMetric
from django.test import TestCase
from factories import BusinessFactory, BusinessUserFactory, CountryFactory, JobFactory, JobPostFactory, \
    TalentFactory, AdminUserFactory, RoleFactory
from jobs.enums import JobStatusType
from jobs.models import JobApplication, Job
from ninja.testing import TestClient
from settings.models import WorkFlowStage


class GetAdminBusinessMetricsTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }

    def test_get_admin_business_metrics_success(self):
        """Test successful retrieval of admin business metrics"""
        response = self.client.get("/business-metrics", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_open_jobs", data)
        self.assertIn("total_applications", data)
        self.assertIn("total_job_shares", data)
        self.assertIn("total_job_views", data)
        self.assertIn("total_interview_invitations", data)
        self.assertIn("active_clients", data)
        self.assertIn("active_users_daily_average", data)
        self.assertIn("active_users_last_7_days", data)
        self.assertIn("job_phases", data)

    def test_get_admin_business_metrics_unauthorized(self):
        """Test admin metrics without authentication"""
        response = self.client.get("/business-metrics")
        self.assertEqual(response.status_code, 401)




class GetTalentMetricsTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }

    def test_get_talent_metrics_success(self):
        """Test successful retrieval of talent metrics"""
        response = self.client.get("/talent-metric", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_talent_signups", data)
        self.assertIn("total_applications", data)
        self.assertIn("active_talents", data)
        self.assertIn("profile_completion_this_week", data)
        self.assertIn("withdrawal_reasons", data)
        self.assertIn("total_withdrawals", data)

    def test_get_talent_metrics_unauthorized(self):
        """Test talent metrics without authentication"""
        response = self.client.get("/talent-metric")
        self.assertEqual(response.status_code, 401)




class GetBusinessesTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        # Create some businesses, some paused and some not
        self.business_paused = BusinessFactory.create(paused=True)
        self.business_active = BusinessFactory.create(paused=False)
        BusinessFactory.create_batch(3)  # Create 3 more businesses (default paused=False)

    def test_get_businesses_success(self):
        """Test successful retrieval of businesses"""
        response = self.client.get("/businesses", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertGreaterEqual(len(data["results"]), 5)

    def test_get_businesses_filter_by_paused(self):
        """Test filtering businesses by paused status"""
        response = self.client.get("/businesses?paused=true", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # All results should be paused businesses
        for business in data["results"]:
            self.assertTrue(business["paused"])

    def test_get_businesses_filter_by_active(self):
        """Test filtering businesses by active status (not paused)"""
        response = self.client.get("/businesses?paused=false", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # All results should be active businesses
        for business in data["results"]:
            self.assertFalse(business["paused"])

    def test_get_businesses_search(self):
        """Test searching businesses by name"""
        # Create a business with a specific name for search
        BusinessFactory.create(name="Unique Search Company")
        response = self.client.get("/businesses?search=Unique Search", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should find at least the business we created
        self.assertGreaterEqual(len(data["results"]), 1)
        # Check that the results contain our search term
        found = False
        for business in data["results"]:
            if "Unique Search" in business["name"]:
                found = True
                break
        self.assertTrue(found)

    def test_get_businesses_unauthorized(self):
        """Test businesses list without authentication"""
        response = self.client.get("/businesses")
        self.assertEqual(response.status_code, 401)


class AddBusinessTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.industry = BusinessIndustry.objects.first()

    def test_add_business_success(self):
        """Test successful creation of a business"""
        data = {
            "name": "Test Company",
            "website": "https://testcompany.com",
            "size": "0-10 Employees",
            "industry": str(self.industry.uid),
            "address": "123 Test Street",
            "description": "A test company description",
            "instagram": "https://instagram.com/test",
            "linkedin": "https://linkedin.com/company/test",
            "facebook": "https://facebook.com/test",
            "twitter_x": "https://twitter.com/test"
        }
        response = self.client.post("/businesses", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], data["name"])

    def test_add_business_unauthorized(self):
        """Test business creation without authentication"""
        data = {"name": "Test Company"}
        response = self.client.post("/businesses", json=data)
        self.assertEqual(response.status_code, 401)


class UpdateBusinessTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()
        self.industry = BusinessIndustry.objects.first()

    def test_update_business_success(self):
        """Test successful update of a business"""
        data = {
            "name": "Updated Company Name",
            "website": "https://updated.com",
            "size": "11-50 Employees",
            "industry": str(self.industry.uid),
        }
        response = self.client.patch(f"/businesses/{self.business.uid}", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, data["name"])

    def test_update_business_unauthorized(self):
        """Test business update without authentication"""
        data = {"name": "Updated Company Name"}
        response = self.client.patch(f"/businesses/{self.business.uid}", json=data)
        self.assertEqual(response.status_code, 401)

    def test_update_business_not_found(self):
        """Test update of non-existent business"""
        data = {"name": "Updated Company Name"}
        response = self.client.patch(f"/businesses/{uuid4()}", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)


class DeleteBusinessTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()

    def test_delete_business_success(self):
        """Test successful deletion of a business"""
        response = self.client.delete(f"/businesses/{self.business.uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Business.objects.filter(uid=self.business.uid).exists())

    def test_delete_business_unauthorized(self):
        """Test business deletion without authentication"""
        response = self.client.delete(f"/businesses/{self.business.uid}")
        self.assertEqual(response.status_code, 401)

    def test_delete_business_not_found(self):
        """Test deletion of non-existent business"""
        response = self.client.delete(f"/businesses/{uuid4()}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)

    def test_delete_business_with_users(self):
        """Test deletion of business with associated users"""
        # Create a business user for this business
        BusinessUserFactory.create(business=self.business)

        response = self.client.delete(f"/businesses/{self.business.uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 204)
        print(response.content)
        # Both business and associated users should be deleted
        self.assertFalse(Business.objects.filter(uid=self.business.uid).exists())
        self.assertFalse(BusinessUser.objects.filter(business__uid=self.business.uid).exists())

    def test_delete_business_with_jobs(self):
        """Test deletion of business with associated jobs"""
        # Create business user and job for this business
        business_user = BusinessUserFactory.create(business=self.business)
        job = JobFactory.create(created_by=business_user)

        response = self.client.delete(f"/businesses/{self.business.uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 204)
        # Business, users, and jobs should all be deleted
        self.assertFalse(Business.objects.filter(uid=self.business.uid).exists())
        self.assertFalse(BusinessUser.objects.filter(business__uid=self.business.uid).exists())
        self.assertFalse(Job.objects.filter(uid=job.uid).exists())




class GetBusinessJobsTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.OWNER.value
        )
        self.job = JobFactory.create(created_by=self.business_user)
        self.job_post = JobPostFactory.create(
            job=self.job,
            recruiter=self.business_user,
            status=JobStatusType.POSTED.value
        )

    def test_get_business_jobs_success(self):
        """Test successful retrieval of business jobs"""
        response = self.client.get(f"/businesses/{self.business.uid}/jobs", headers=self.auth_headers)
        print(response.content)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertIn("jobs_created", data)
        self.assertIn("open_jobs", data)
        self.assertIn("applications", data)

    def test_get_business_jobs_unauthorized(self):
        """Test business jobs without authentication"""
        response = self.client.get(f"/businesses/{self.business.uid}/jobs")
        self.assertEqual(response.status_code, 401)


class GetBusinessUsersTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()
        # Create some business users, some active and some not
        self.business_user_active = BusinessUserFactory.create(business=self.business, user__is_active=True)
        self.business_user_inactive = BusinessUserFactory.create(business=self.business, user__is_active=False)
        BusinessUserFactory.create_batch(2, business=self.business)  # Create 2 more business users

    def test_get_business_users_success(self):
        """Test successful retrieval of business users"""
        response = self.client.get(f"/businesses/{self.business.uid}/users", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)

    def test_get_business_users_filter_by_active(self):
        """Test filtering business users by active status"""
        response = self.client.get(f"/businesses/{self.business.uid}/users?active=true", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should only return active business users
        # Check that our known active user is in the results
        active_user_ids = [str(user["uid"]) for user in data["results"]]
        self.assertIn(str(self.business_user_active.uid), active_user_ids)
        # And that our known inactive user is NOT in the results
        inactive_user_ids = [str(user["uid"]) for user in data["results"]]
        self.assertNotIn(str(self.business_user_inactive.uid), inactive_user_ids)

    def test_get_business_users_filter_by_inactive(self):
        """Test filtering business users by inactive status"""
        response = self.client.get(f"/businesses/{self.business.uid}/users?active=false", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should only return inactive business users
        # Check that our known inactive user is in the results
        inactive_user_ids = [str(user["uid"]) for user in data["results"]]
        self.assertIn(str(self.business_user_inactive.uid), inactive_user_ids)
        # And that our known active user is NOT in the results
        active_user_ids = [str(user["uid"]) for user in data["results"]]
        self.assertNotIn(str(self.business_user_active.uid), active_user_ids)

    def test_get_business_users_search(self):
        """Test searching business users by name"""
        # Create a business user with a specific name for search
        businessuser = BusinessUserFactory.create(business=self.business)
        businessuser.user.first_name = "Unique"
        businessuser.user.last_name = "Search user"
        businessuser.user.save()

        response = self.client.get(f"/businesses/{self.business.uid}/users?search=Unique Search", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should find at least the business user we created
        self.assertGreaterEqual(len(data["results"]), 1)
        # Check that the results contain our search term in full name
        found = False
        for user in data["results"]:
            full_name = user["full_name"]
            if "Unique Search" in full_name:
                found = True
                break
        self.assertTrue(found)

    def test_get_business_users_unauthorized(self):
        """Test business users without authentication"""
        response = self.client.get(f"/businesses/{self.business.uid}/users")
        self.assertEqual(response.status_code, 401)


class AddBusinessUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()

    def test_add_business_user_success(self):
        """Test successful creation of a business user"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "newuser@example.com",
            "role": BusinessUserRoleType.TEAM_MEMBER.value
        }
        response = self.client.post(f"/businesses/{self.business.uid}/users", json=data, headers=self.auth_headers)
        print(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], data["email"])

    def test_add_business_user_unauthorized(self):
        """Test business user creation without authentication"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "newuser@example.com",
            "role": BusinessUserRoleType.TEAM_MEMBER.value
        }
        response = self.client.post(f"/businesses/{self.business.uid}/users", json=data)
        self.assertEqual(response.status_code, 401)


class UpdateBusinessUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(business=self.business)

    def test_update_business_user_success(self):
        """Test successful update of a business user"""
        data = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "role": BusinessUserRoleType.ADMIN.value
        }
        response = self.client.patch(
            f"/businesses/users/{self.business_user.uid}",
            json=data,
            headers=self.auth_headers
        )
        print(response.content)
        self.assertEqual(response.status_code, 200)
        self.business_user.refresh_from_db()
        self.assertEqual(self.business_user.user.first_name, data["first_name"])

    def test_update_business_user_unauthorized(self):
        """Test business user update without authentication"""
        data = {"first_name": "Updated"}
        response = self.client.patch(
            f"/businesses/users/{self.business_user.uid}",
            json=data
        )
        self.assertEqual(response.status_code, 401)


class DeleteBusinessUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()
        self.owner = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.OWNER.value,
            user=self.business.created_by
        )
        self.team_member = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.TEAM_MEMBER.value
        )

    def test_delete_business_user_success(self):
        """Test successful deletion of a business user"""
        response = self.client.delete(
            f"/businesses/users/{self.team_member.uid}",
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(BusinessUser.objects.filter(uid=self.team_member.uid).first())

    def test_delete_business_user_cannot_delete_owner(self):
        """Test that an owner cannot be deleted"""
        response = self.client.delete(
            f"/businesses/users/{self.owner.uid}",
            headers=self.auth_headers
        )
        print(response.content)
        self.assertEqual(response.status_code, 400)

    def test_delete_business_user_unauthorized(self):
        """Test business user deletion without authentication"""
        response = self.client.delete(
            f"/businesses/users/{self.team_member.uid}"
        )
        self.assertEqual(response.status_code, 401)


class LoginAsBusinessUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(business=self.business)

    def test_login_as_business_user_success(self):
        """Test successful login as business user"""
        response = self.client.post(
            f"/businesses/users/{self.business_user.uid}/login",
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("email", data)
        self.assertEqual(data["email"], self.business_user.user.email)

    def test_login_as_business_user_unauthorized(self):
        """Test login as business user without authentication"""
        response = self.client.post(
            f"/businesses/users/{self.business_user.uid}/login"
        )
        self.assertEqual(response.status_code, 401)

    def test_login_as_business_user_not_found(self):
        """Test login as non-existent business user"""
        response = self.client.post(
            f"/businesses/users/{uuid4()}/login",
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 404)  # ValidationError returns 422


class DeactivateBusinessUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business=self.business,
            status=BusinessUserStatusType.ACTIVE.value
        )
        self.test_data = {
            "is_active": False
        }

    def test_deactivate_business_user_success(self):
        """Test successful deactivation of business user"""
        response = self.client.post(
            f"/businesses/users/{self.business_user.uid}/account-status",
            headers=self.auth_headers,
            json=self.test_data
        )
        self.assertEqual(response.status_code, 200)
        self.business_user.refresh_from_db()
        self.assertEqual(self.business_user.status, BusinessUserStatusType.INACTIVE.value)

    def test_deactivate_business_user_unauthorized(self):
        """Test business user deactivation without authentication"""
        response = self.client.post(
            f"/businesses/users/{self.business_user.uid}/account-status",
            json=self.test_data

        )
        self.assertEqual(response.status_code, 401)

    def test_deactivate_business_user_not_found(self):
        """Test deactivation of non-existent business user"""
        response = self.client.post(
            f"/businesses/users/{uuid4()}/account-status",
            headers=self.auth_headers,
            json=self.test_data
        )
        self.assertEqual(response.status_code, 404)  # ValidationError returns 422


class GetTalentUsersTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        # Create some talents, some active and some not
        self.talent_active = TalentFactory.create(user__is_active=True)
        self.talent_inactive = TalentFactory.create(user__is_active=False)
        TalentFactory.create_batch(3)  # Create 3 more talents (default active=True)

    def test_get_talent_users_success(self):
        """Test successful retrieval of talent users"""
        response = self.client.get("/talents", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertGreaterEqual(len(data["results"]), 5)

    def test_get_talent_users_filter_by_active(self):
        """Test filtering talent users by active status"""
        response = self.client.get("/talents?active=true", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should only return active talents
        # Check that our known active talent is in the results
        active_talent_ids = [str(talent["uid"]) for talent in data["results"]]
        self.assertIn(str(self.talent_active.uid), active_talent_ids)
        # And that our known inactive talent is NOT in the results
        inactive_talent_ids = [str(talent["uid"]) for talent in data["results"]]
        self.assertNotIn(str(self.talent_inactive.uid), inactive_talent_ids)

    def test_get_talent_users_filter_by_inactive(self):
        """Test filtering talent users by inactive status"""
        response = self.client.get("/talents?active=false", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should only return inactive talents
        # Check that our known inactive talent is in the results
        inactive_talent_ids = [str(talent["uid"]) for talent in data["results"]]
        self.assertIn(str(self.talent_inactive.uid), inactive_talent_ids)
        # And that our known active talent is NOT in the results
        active_talent_ids = [str(talent["uid"]) for talent in data["results"]]
        self.assertNotIn(str(self.talent_active.uid), active_talent_ids)

    def test_get_talent_users_search(self):
        """Test searching talents by name"""
        # Create a talent with a specific name for search
        talent = TalentFactory.create()
        talent.user.first_name = "Unique"
        talent.user.last_name = "Search person"
        talent.user.save()
        response = self.client.get("/talents?search=Unique Search", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should find at least the talent we created
        self.assertGreaterEqual(len(data["results"]), 1)
        # Check that the results contain our search term in full name
        found = False
        for talent in data["results"]:
            full_name = talent["full_name"]
            if "Unique Search" in full_name:
                found = True
                break
        self.assertTrue(found)

    def test_get_talent_users_unauthorized(self):
        """Test talent users list without authentication"""
        response = self.client.get("/talents")
        self.assertEqual(response.status_code, 401)


class GetTalentUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.talent = TalentFactory.create()

    def test_get_talent_user_success(self):
        """Test successful retrieval of a talent user"""
        response = self.client.get(f"/talents/{self.talent.uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["uid"], str(self.talent.uid))

    def test_get_talent_user_unauthorized(self):
        """Test talent user retrieval without authentication"""
        response = self.client.get(f"/talents/{self.talent.uid}")
        self.assertEqual(response.status_code, 401)

    def test_get_talent_user_not_found(self):
        """Test retrieval of non-existent talent user"""
        response = self.client.get(f"/talents/{uuid4()}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)


class GetTalentApplicationsTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.talent = TalentFactory.create()
        self.business = BusinessFactory.create()
        self.business_user = BusinessUserFactory.create(
            business=self.business,
            role=BusinessUserRoleType.OWNER.value
        )
        self.stage = WorkFlowStage.objects.filter(created_by__business=self.business).first()
        self.job = JobFactory.create(created_by=self.business_user)
        self.job_post = JobPostFactory.create(job=self.job)
        self.application = JobApplication.objects.create(
            applicant=self.talent,
            job_post=self.job_post,
            stage=self.stage
        )

    def test_get_talent_applications_success(self):
        """Test successful retrieval of talent applications"""
        response = self.client.get(f"/talents/{self.talent.uid}/applications", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertIn("applications", data)
        self.assertIn("rejected", data)
        self.assertIn("withdrawals", data)

    def test_get_talent_applications_unauthorized(self):
        """Test talent applications without authentication"""
        response = self.client.get(f"/talents/{self.talent.uid}/applications")
        self.assertEqual(response.status_code, 401)

    def test_get_talent_applications_not_found(self):
        """Test applications for non-existent talent"""
        response = self.client.get(f"/talents/{uuid4()}/applications", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)


class CreateTalentUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.country = CountryFactory.create()
        self.role = RoleFactory.create()  # Using Role factory for talent role

    def test_create_talent_user_success(self):
        """Test successful creation of a talent user"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "talent@example.com",
            "country": str(self.country.uid),
            "role": str(self.role.uid),
            "phone_code": "+1",
            "phone_number": "1234567890"
        }
        response = self.client.post("/talents", json=data, headers=self.auth_headers)
        print("Check: ", response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], data["email"])

    def test_create_talent_user_unauthorized(self):
        """Test talent user creation without authentication"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "talent@example.com"
        }
        response = self.client.post("/talents", json=data)
        print(response.json())
        self.assertEqual(response.status_code, 401)

    def test_create_talent_user_missing_required_fields(self):
        """Test talent user creation with missing required fields"""
        data = {
            "first_name": "John"
            # Missing last_name and email
        }
        response = self.client.post("/talents", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 400)

    def test_create_talent_user_duplicate_email(self):
        """Test talent user creation with duplicate email"""
        existing_talent = TalentFactory.create()
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": existing_talent.user.email
        }
        response = self.client.post("/talents", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 400)


class UpdateTalentUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.talent = TalentFactory.create()
        self.country = CountryFactory.create()

    def test_update_talent_user_success(self):
        """Test successful update of a talent user"""
        data = {
            "first_name": "Updated",
            "last_name": "Name",
            "country": str(self.country.uid)
        }
        response = self.client.patch(
            f"/talents/{self.talent.uid}",
            json=data,
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.talent.refresh_from_db()
        self.assertEqual(self.talent.user.first_name, data["first_name"])

    def test_update_talent_user_unauthorized(self):
        """Test talent user update without authentication"""
        data = {"first_name": "Updated"}
        response = self.client.patch(f"/talents/{self.talent.uid}", json=data)
        self.assertEqual(response.status_code, 401)

    def test_update_talent_user_not_found(self):
        """Test update of non-existent talent user"""
        data = {"first_name": "Updated"}
        response = self.client.patch(f"/talents/{uuid4()}", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)




class LoginAsTalentTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.talent = TalentFactory.create()

    def test_login_as_talent_success(self):
        """Test successful login as talent"""
        response = self.client.post(
            f"/talents/{self.talent.uid}/login",
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("email", data)
        self.assertEqual(data["email"], self.talent.user.email)

    def test_login_as_talent_unauthorized(self):
        """Test login as talent without authentication"""
        response = self.client.post(
            f"/talents/{self.talent.uid}/login"
        )
        self.assertEqual(response.status_code, 401)

    def test_login_as_talent_not_found(self):
        """Test login as non-existent talent"""
        response = self.client.post(
            f"/talents/{uuid4()}/login",
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 404)


class BanTalentTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.talent = TalentFactory.create()

    def test_ban_talent_success(self):
        """Test successful banning of a talent"""
        response = self.client.post(
            f"/talents/{self.talent.uid}/ban",
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Talent.objects.filter(uid=self.talent.uid).exists())
        self.assertFalse(User.objects.filter(id=self.talent.user.id).exists())
        self.assertTrue(BannedAccount.objects.filter(email__iexact=self.talent.user.email).exists())
        self.assertEqual(response.json(), {"message": "Talent account has been banned successfully"})

    def test_ban_talent_unauthorized(self):
        """Test banning talent without authentication"""
        response = self.client.post(
            f"/talents/{self.talent.uid}/ban"
        )
        self.assertEqual(response.status_code, 401)

    def test_ban_talent_not_found(self):
        """Test banning non-existent talent"""
        response = self.client.post(
            f"/talents/{uuid4()}/ban",
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 404)


class DeactivateTalentTestCase(TestCase):
    """Test cases for admin metrics API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        
        # Create test data for metrics
        self.jan_2024 = date(2024, 1, 1)
        self.feb_2024 = date(2024, 2, 1)
        self.mar_2024 = date(2024, 3, 1)
        
        # Create test PageMetric data
        self.page_metric1 = PageMetric.objects.create(
            path="/dashboard",
            month=self.jan_2024,
            count=100,
            total_time=5000.0,
            updated_at=datetime(2024, 1, 15, tzinfo=dt_timezone.utc)
        )
        
        self.page_metric2 = PageMetric.objects.create(
            path="/dashboard",
            month=self.feb_2024,
            count=200,
            total_time=8000.0,
            updated_at=datetime(2024, 2, 15, tzinfo=dt_timezone.utc)
        )
        
        # Create test APIMetric data
        self.api_metric1 = APIMetric.objects.create(
            path="/api/v1/users/",
            month=self.jan_2024,
            count=150,
            total_time=7500.0,
            updated_at=datetime(2024, 1, 15, tzinfo=dt_timezone.utc)
        )
        
        self.api_metric2 = APIMetric.objects.create(
            path="/api/v1/users/",
            month=self.feb_2024,
            count=250,
            total_time=10000.0,
            updated_at=datetime(2024, 2, 15, tzinfo=dt_timezone.utc)
        )
        
        # Create test Talent data for signups and profile completion
        self.talent1 = TalentFactory.create(
            created_at=datetime(2024, 1, 15, tzinfo=dt_timezone.utc)
        )
        self.talent2 = TalentFactory.create(
            created_at=datetime(2024, 2, 15, tzinfo=dt_timezone.utc)
        )
        self.talent3 = TalentFactory.create(
            created_at=datetime(2024, 3, 15, tzinfo=dt_timezone.utc)
        )

    def test_get_page_metrics_success(self):
        """Test successful retrieval of page metrics"""
        response = self.client.get("/metrics/pages", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        # Just check that we get a successful response with some data
        data = response.json()
        self.assertIsInstance(data, (dict, list))

    def test_get_page_metrics_unauthorized(self):
        """Test page metrics endpoint without authentication"""
        response = self.client.get("/metrics/pages")
        self.assertEqual(response.status_code, 401)

    def test_get_api_metrics_success(self):
        """Test successful retrieval of API metrics"""
        response = self.client.get("/metrics/api", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        # Just check that we get a successful response with some data
        data = response.json()
        self.assertIsInstance(data, (dict, list))

    def test_get_api_metrics_unauthorized(self):
        """Test API metrics endpoint without authentication"""
        response = self.client.get("/metrics/api")
        self.assertEqual(response.status_code, 401)

    def test_get_talent_signups_success(self):
        """Test successful retrieval of talent signups"""
        response = self.client.get("/metrics/talent/signups", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        # Just check that we get a successful response with some data
        data = response.json()
        self.assertIsInstance(data, (dict, list))

    def test_get_talent_signups_with_filters(self):
        """Test talent signups with date filters"""
        response = self.client.get(
            "/metrics/talent/signups?start_date=2024-02-01&end_date=2024-02-29", 
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        # Just check that we get a successful response
        data = response.json()
        self.assertIsInstance(data, (dict, list))

    def test_get_talent_signups_unauthorized(self):
        """Test talent signups endpoint without authentication"""
        response = self.client.get("/metrics/talent/signups")
        self.assertEqual(response.status_code, 401)

    def test_get_talent_profile_completion_success(self):
        """Test successful retrieval of talent profile completion"""
        response = self.client.get("/metrics/talent/profile-completion", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        # Just check that we get a successful response with some data
        data = response.json()
        self.assertIsInstance(data, (dict, list))

    def test_get_talent_profile_completion_with_filters(self):
        """Test talent profile completion with date filters"""
        response = self.client.get(
            "/metrics/talent/profile-completion?start_date=2024-01-01&end_date=2024-01-31", 
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        # Just check that we get a successful response
        data = response.json()
        self.assertIsInstance(data, (dict, list))

    def test_get_talent_profile_completion_unauthorized(self):
        """Test talent profile completion endpoint without authentication"""
        response = self.client.get("/metrics/talent/profile-completion")
        self.assertEqual(response.status_code, 401)

    def test_metrics_pagination(self):
        """Test that metrics endpoints support pagination parameters"""
        response = self.client.get("/metrics/pages?page=1&page_size=10", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        # Just check that pagination parameters are accepted without error
        data = response.json()
        self.assertIsInstance(data, (dict, list))


class PauseResumeBusinessTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.business = BusinessFactory.create()

    def test_pause_business_success(self):
        """Test successful pausing of a business"""
        data = {"action": "pause"}
        response = self.client.post(f"/businesses/{self.business.uid}/resumption", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.business.refresh_from_db()
        self.assertTrue(self.business.paused)

    def test_resume_business_success(self):
        """Test successful resuming of a business"""
        # First pause the business
        self.business.paused = True
        self.business.save()

        data = {"action": "resume"}
        response = self.client.post(f"/businesses/{self.business.uid}/resumption", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.business.refresh_from_db()
        self.assertFalse(self.business.paused)

    def test_pause_resume_business_unauthorized(self):
        """Test pause/resume business without authentication"""
        data = {"action": "pause"}
        response = self.client.post(f"/businesses/{self.business.uid}/resumption", json=data)
        self.assertEqual(response.status_code, 401)

    def test_pause_resume_business_not_found(self):
        """Test pause/resume of non-existent business"""
        data = {"action": "pause"}
        response = self.client.post(f"/businesses/{uuid4()}/resumption", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)

    def test_pause_resume_business_invalid_action(self):
        """Test pause/resume with invalid action"""
        data = {"action": "invalid"}
        response = self.client.post(f"/businesses/{self.business.uid}/resumption", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 422)

    def test_pause_resume_business_missing_action(self):
        """Test pause/resume with missing action"""
        data = {}
        response = self.client.post(f"/businesses/{self.business.uid}/resumption", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 422)  # Validation error


class GetBannedAccountsTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        # Create a banned talent account
        self.talent = TalentFactory.create()
        from accounts.models import BannedAccount
        self.banned_account = BannedAccount.objects.create(
            email=self.talent.user.email,
            account_type=UserType.TALENT.value
        )
        # Create a banned business user account
        self.business_user = BusinessUserFactory.create()
        self.business_user.user.is_active = False
        self.business_user.user.save()
        from accounts.models import BannedAccount
        self.banned_business_account = BannedAccount.objects.create(
            email=self.business_user.user.email,
            account_type=UserType.BUSINESS.value
        )

    def test_get_banned_accounts_success(self):
        """Test successful retrieval of banned accounts"""
        response = self.client.get("/banned-accounts", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Should have at least 2 banned accounts (1 talent, 1 business user)
        self.assertGreaterEqual(len(data["results"]), 2)

    def test_get_banned_accounts_filter_by_talent(self):
        """Test filtering banned accounts by talent account type"""
        response = self.client.get("/banned-accounts?account_type=talent", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # All results should be talent accounts
        for account in data["results"]:
            self.assertEqual(account["account_type"], "talent")

    def test_get_banned_accounts_filter_by_business_user(self):
        """Test filtering banned accounts by business user account type"""
        response = self.client.get("/banned-accounts?account_type=business", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # All results should be business user accounts
        for account in data["results"]:
            self.assertEqual(account["account_type"], "business")

    def test_get_banned_accounts_unauthorized(self):
        """Test banned accounts list without authentication"""
        response = self.client.get("/banned-accounts")
        self.assertEqual(response.status_code, 401)


class UnbanAccountTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        # Create a talent and ban it to get a banned account
        self.talent = TalentFactory.create()
        from accounts.models import BannedAccount
        self.banned_account = BannedAccount.objects.create(
            email=self.talent.user.email,
            account_type=UserType.TALENT.value
        )

    def test_unban_account_success(self):
        """Test successful unbanning of an account"""
        response = self.client.post(f"/banned-accounts/{self.banned_account.uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        # The banned account should be deleted
        self.assertFalse(BannedAccount.objects.filter(uid=self.banned_account.uid).exists())

    def test_unban_account_unauthorized(self):
        """Test unbanning account without authentication"""
        response = self.client.post(f"/banned-accounts/{self.banned_account.uid}")
        self.assertEqual(response.status_code, 401)

    def test_unban_account_not_found(self):
        """Test unbanning non-existent account"""
        response = self.client.post(f"/banned-accounts/{uuid4()}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)


class GetBusinessDetailTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.admin_user = AdminUserFactory.create()
        self.user = self.admin_user.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        # Create a business with a logo to avoid validation issues in the detail endpoint
        self.business = BusinessFactory.create(
            description="Test business description"
        )
        # Set a logo file path (we don't need an actual file for testing)
        self.business.logo = "media/logo/test_logo.png"
        self.business.save()

    def test_get_business_success(self):
        """Test successful retrieval of a business by UID"""
        response = self.client.get(f"/businesses/{self.business.uid}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["uid"], str(self.business.uid))
        self.assertEqual(data["name"], self.business.name)
        self.assertEqual(data["website"], self.business.website)
        self.assertEqual(int(data["size"]), self.business.size)
        self.assertEqual(data["description"], self.business.description)

    def test_get_business_unauthorized(self):
        """Test business retrieval without authentication"""
        response = self.client.get(f"/businesses/{self.business.uid}")
        self.assertEqual(response.status_code, 401)

    def test_get_business_not_found(self):
        """Test retrieval of non-existent business"""
        response = self.client.get(f"/businesses/{uuid4()}", headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)


class GetAdminUsersTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.super_admin = AdminUserFactory.create(role="super_admin")
        self.user = self.super_admin.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        # Create some admin users, some active and some not
        self.admin_active = AdminUserFactory.create(role="admin")
        self.admin_active.user.is_active = True
        self.admin_active.user.save()
        self.admin_inactive = AdminUserFactory.create(role="admin")
        self.admin_inactive.user.is_active = False
        self.admin_inactive.user.save()
        AdminUserFactory.create_batch(2)  # Create 2 more admin users

    def test_get_admin_users_success(self):
        """Test successful retrieval of admin users"""
        response = self.client.get("/admin-users", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertGreaterEqual(len(data["results"]), 4)

    def test_get_admin_users_filter_by_active(self):
        """Test filtering admin users by active status"""
        response = self.client.get("/admin-users?active=true", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Check that our known active admin is in the results
        active_admin_ids = [str(admin["uid"]) for admin in data["results"]]
        self.assertIn(str(self.admin_active.uid), active_admin_ids)
        # And that our known inactive admin is NOT in the results
        inactive_admin_ids = [str(admin["uid"]) for admin in data["results"]]
        self.assertNotIn(str(self.admin_inactive.uid), inactive_admin_ids)

    def test_get_admin_users_filter_by_inactive(self):
        """Test filtering admin users by inactive status"""
        response = self.client.get("/admin-users?active=false", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        # Check that our known inactive admin is in the results
        inactive_admin_ids = [str(admin["uid"]) for admin in data["results"]]
        self.assertIn(str(self.admin_inactive.uid), inactive_admin_ids)
        # And that our known active admin is NOT in the results
        self.assertNotIn(str(self.admin_active.uid), inactive_admin_ids)

    def test_get_admin_users_unauthorized(self):
        """Test admin users list without authentication"""
        response = self.client.get("/admin-users")
        self.assertEqual(response.status_code, 401)

    def test_get_admin_users_not_super_admin(self):
        """Test that non-super admin cannot access admin users list"""
        # Create a regular admin user
        regular_admin = AdminUserFactory.create(role="admin")
        regular_auth_headers = {
            "authorization": f"Bearer {regular_admin.user.token}"
        }
        response = self.client.get("/admin-users", headers=regular_auth_headers)
        self.assertEqual(response.status_code, 403)


class UpdateAdminUsersStatusTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.super_admin = AdminUserFactory.create(role="super_admin")
        self.user = self.super_admin.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }
        self.admin1 = AdminUserFactory.create(user__is_active=True, role="admin")
        self.admin2 = AdminUserFactory.create(user__is_active=True, role="admin")

    def test_update_admin_users_status_block_success(self):
        """Test successful blocking of admin users"""
        data = {
            "action": "block",
            "uids": [str(self.admin1.uid), str(self.admin2.uid)]
        }
        response = self.client.patch("/admin-users", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.admin1.refresh_from_db()
        self.admin2.refresh_from_db()
        self.assertFalse(self.admin1.user.is_active)
        self.assertFalse(self.admin2.user.is_active)

    def test_update_admin_users_status_unblock_success(self):
        """Test successful unblocking of admin users"""
        # First block the admins
        self.admin1.user.is_active = False
        self.admin1.user.save()
        self.admin2.user.is_active = False
        self.admin2.user.save()

        data = {
            "action": "unblock",
            "uids": [str(self.admin1.uid), str(self.admin2.uid)]
        }
        response = self.client.patch("/admin-users", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.admin1.refresh_from_db()
        self.admin2.refresh_from_db()
        self.assertTrue(self.admin1.user.is_active)
        self.assertTrue(self.admin2.user.is_active)

    def test_update_admin_users_status_unauthorized(self):
        """Test admin users status update without authentication"""
        data = {
            "action": "block",
            "uids": [str(self.admin1.uid)]
        }
        response = self.client.patch("/admin-users", json=data)
        self.assertEqual(response.status_code, 401)

    def test_update_admin_users_status_not_super_admin(self):
        """Test that non-super admin cannot update admin users status"""
        regular_admin = AdminUserFactory.create(role="admin")
        regular_auth_headers = {
            "authorization": f"Bearer {regular_admin.user.token}"
        }
        data = {
            "action": "block",
            "uids": [str(self.admin1.uid)]
        }
        response = self.client.patch("/admin-users", json=data, headers=regular_auth_headers)
        self.assertEqual(response.status_code, 403)

    def test_update_admin_users_status_invalid_action(self):
        """Test admin users status update with invalid action"""
        data = {
            "action": "invalid",
            "uids": [str(self.admin1.uid)]
        }
        response = self.client.patch("/admin-users", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 422)


class InviteAdminUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.super_admin = AdminUserFactory.create(role="super_admin")
        self.user = self.super_admin.user
        self.auth_headers = {
            "authorization": f"Bearer {self.user.token}"
        }

    def test_invite_admin_user_success(self):
        """Test successful invitation of an admin user"""
        data = {
            "email": "newadmin@example.com",
            "fullname": "John Doe"
        }
        self.assertFalse(AdminUserInvite.objects.filter(email="newadmin@example.com").exists())
        response = self.client.post("/admin-users", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(AdminUserInvite.objects.filter(email="newadmin@example.com").exists())

    def test_invite_admin_user_unauthorized(self):
        """Test admin user invitation without authentication"""
        data = {
            "email": "newadmin@example.com",
            "fullname": "John Doe"
        }
        response = self.client.post("/admin-users", json=data)
        self.assertEqual(response.status_code, 401)

    def test_invite_admin_user_not_super_admin(self):
        """Test that non-super admin cannot invite admin users"""
        regular_admin = AdminUserFactory.create(role="admin")
        regular_auth_headers = {
            "authorization": f"Bearer {regular_admin.user.token}"
        }
        data = {
            "email": "newadmin@example.com",
            "fullname": "John Doe"
        }
        response = self.client.post("/admin-users", json=data, headers=regular_auth_headers)
        self.assertEqual(response.status_code, 403)

    def test_invite_admin_user_duplicate_email(self):
        """Test admin user invitation with duplicate email"""
        existing_admin = AdminUserFactory.create()
        data = {
            "email": existing_admin.user.email,
            "fullname": "John Doe"
        }
        response = self.client.post("/admin-users", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 400)

    def test_invite_admin_user_existing_user_email(self):
        """Test admin user invitation with existing user email"""
        existing_talent = TalentFactory.create()
        data = {
            "email": existing_talent.user.email,
            "fullname": "John Doe"
        }
        response = self.client.post("/admin-users", json=data, headers=self.auth_headers)
        self.assertEqual(response.status_code, 400)


class UpdateAdminUserTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.super_admin = AdminUserFactory.create(role="super_admin")
        self.super_admin_auth_headers = {
            "authorization": f"Bearer {self.super_admin.user.token}"
        }
        self.admin = AdminUserFactory.create(role="admin")
        self.admin_auth_headers = {
            "authorization": f"Bearer {self.admin.user.token}"
        }

    def test_update_admin_user_success_as_super_admin(self):
        """Test successful update of an admin user by super admin"""
        data = {
            "email": "updated@example.com",
            "fullname": "Updated Name",
            "role": "admin"
        }
        response = self.client.patch(
            f"/admin-users/{self.admin.uid}",
            json=data,
            headers=self.super_admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.user.email, data["email"])

    def test_update_admin_user_success_self_update(self):
        """Test successful self-update of admin user"""
        data = {
            "email": "selfupdated@example.com",
            "fullname": "Self Updated Name"
        }
        response = self.client.patch(
            f"/admin-users/{self.admin.uid}",
            json=data,
            headers=self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.user.email, data["email"])

    def test_update_admin_user_unauthorized(self):
        """Test admin user update without authentication"""
        data = {"email": "updated@example.com", "fullname": "Updated Name"}
        response = self.client.patch(f"/admin-users/{self.admin.uid}", json=data)
        self.assertEqual(response.status_code, 401)

    def test_update_admin_user_not_found(self):
        """Test update of non-existent admin user"""
        data = {"email": "updated@example.com", "fullname": "Updated Name"}
        response = self.client.patch(
            f"/admin-users/{uuid4()}",
            json=data,
            headers=self.super_admin_auth_headers
        )
        self.assertEqual(response.status_code, 404)

    def test_update_admin_user_unauthorized_other_user(self):
        """Test that admin cannot update another admin user"""
        other_admin = AdminUserFactory.create(role="admin")
        data = {
            "email": "updated@example.com",
            "fullname": "Updated Name"
        }
        response = self.client.patch(
            f"/admin-users/{other_admin.uid}",
            json=data,
            headers=self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 403)

    def test_update_admin_user_role_by_non_super_admin(self):
        """Test that non-super admin cannot update role"""
        data = {
            "email": "updated@example.com",
            "fullname": "Updated Name",
            "role": "super_admin"
        }
        response = self.client.patch(
            f"/admin-users/{self.admin.uid}",
            json=data,
            headers=self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        # Role should not have been updated
        self.assertEqual(self.admin.role, "admin")


class AcceptAdminInviteTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        from accounts.models import AdminUserInvite
        self.invite = AdminUserInvite.objects.create(
            email="invitee@example.com",
            first_name="John",
            last_name="Doe"
        )

    def test_accept_admin_invite_success(self):
        """Test successful acceptance of admin invite"""
        data = {
            "code": str(self.invite.uid),
            "password": "SecurePassword123!"
        }
        response = self.client.post("/accept-admin-invite", json=data)
        self.assertEqual(response.status_code, 200)
        # Verify the admin user was created
        from accounts.models import AdminUser
        self.assertTrue(AdminUser.objects.filter(user__email=self.invite.email).exists())
        # Verify the invite was deleted
        self.assertFalse(AdminUserInvite.objects.filter(uid=self.invite.uid).exists())

    def test_accept_admin_invite_invalid_code(self):
        """Test admin invite acceptance with invalid code"""
        data = {
            "code": "invalid-code",
            "password": "SecurePassword123!"
        }
        response = self.client.post("/accept-admin-invite", json=data)
        self.assertEqual(response.status_code, 400)

    def test_accept_admin_invite_expired_code(self):
        """Test admin invite acceptance with expired/non-existent code"""
        data = {
            "code": str(uuid4()),
            "password": "SecurePassword123!"
        }
        response = self.client.post("/accept-admin-invite", json=data)
        self.assertEqual(response.status_code, 404)

    def test_accept_admin_invite_already_accepted(self):
        """Test admin invite acceptance when already accepted"""
        # First accept the invite
        data = {
            "code": str(self.invite.uid),
            "password": "SecurePassword123!"
        }
        response = self.client.post("/accept-admin-invite", json=data)
        self.assertEqual(response.status_code, 200)

        # Try to accept again
        response = self.client.post("/accept-admin-invite", json=data)
        self.assertEqual(response.status_code, 404)

    def test_accept_admin_invite_email_already_exists(self):
        """Test admin invite acceptance when email already exists"""
        # Create a user with the same email as the invite
        TalentFactory.create(user__email=self.invite.email)
        data = {
            "code": str(self.invite.uid),
            "password": "SecurePassword123!"
        }
        response = self.client.post("/accept-admin-invite", json=data)
        self.assertEqual(response.status_code, 400)


