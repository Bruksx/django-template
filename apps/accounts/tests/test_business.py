from accounts.models import User, VerificationCode, Business, BusinessUser
from django.test import TestCase
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth
from apps.accounts.business_views import router


class ValidateOtpTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.url = "/validate-otp"  
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
