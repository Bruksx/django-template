from datetime import timedelta

from accounts.models import VerificationCode
from auth.views import router
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from factories import TalentFactory
from ninja.testing import TestClient

User = get_user_model()

class LoginEndpointTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.login_url = '/login'

    def test_login_successful(self):
        user = User.objects.create_user(email='testuser@example.com', password='securepassword')
        user.update(email_verified=True)
        data = {
            'email': 'testuser@example.com',
            'password': 'securepassword'
        }
        response = self.client.post(self.login_url, json=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['email'], 'testuser@example.com')

    def test_login_unsuccessful_with_wrong_password(self):
        User.objects.create_user(email='testuser@example.com', password='securepassword',
                                 email_verified=True)
        
        data = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, json=data, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['detail'], 'Invalid login credentials')

    def test_login_unsuccessful_with_non_existent_user(self):
        data = {
            'email': 'nonexistentuser@example.com',
            'password': 'any_password'
        }
        response = self.client.post(self.login_url, json=data, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['detail'], "You don't have an account with us")


class ResetPasswordAPITests(TestCase):
    def setUp(self):
        self.url = "reset-password"
        self.client = TestClient(router)
        self.talent = TalentFactory.create()
        code = VerificationCode(email=self.talent.user.email)
        code.save()
        self.code = code
        self.data = {
            "otp": code.code,
            "email": self.talent.user.email,
            "password": "TestPassKey12*"
        }


    def test_reset_password(self):
        self.assertFalse(self.talent.user.check_password(self.data["password"]))
        self.assertIsNotNone(VerificationCode.objects.filter(email=self.talent.user.email).first())
        response = self.client.post(
            path=self.url,
            json=self.data
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(VerificationCode.objects.filter(email=self.talent.user.email).first())
        self.talent.refresh_from_db()
        self.assertTrue(self.talent.user.check_password(self.data["password"]))


    def test_expired_otp(self):
        self.code.expires_at = timezone.now() - timedelta(days=10)
        self.code.save()
        response = self.client.post(
            path=self.url,
            json=self.data
        )
        self.assertEqual(response.status_code, 400)
        self.assertIsNotNone(VerificationCode.objects.filter(email=self.talent.user.email).first())
        self.assertFalse(self.talent.user.check_password(self.data["password"]))

    def test_wrong_otp(self):
        self.data["otp"] = f"4{self.data['otp']}"
        response = self.client.post(
            path=self.url,
            json=self.data
        )
        self.assertEqual(response.status_code, 400)
        self.assertIsNotNone(VerificationCode.objects.filter(email=self.talent.user.email).first())
        self.assertFalse(self.talent.user.check_password(self.data["password"]))

    def test_wrong_email(self):
        self.data["email"] = f"x{self.data['email']}"
        response = self.client.post(
            path=self.url,
            json=self.data
        )
        self.assertEqual(response.status_code, 400)
        self.assertIsNotNone(VerificationCode.objects.filter(email=self.talent.user.email).first())
        self.assertFalse(self.talent.user.check_password(self.data["password"]))

    def test_invalid_password(self):
        password_tests = (
            "testpassword",
            "TestPassword",
            "Te5TPass0rd",
            "T%password"
        )
        for password in password_tests:
            self.data["password"] = password
            response = self.client.post(
                path=self.url,
                json=self.data
            )
            self.assertEqual(response.status_code, 400)
            self.assertIsNotNone(VerificationCode.objects.filter(email=self.talent.user.email).first())
            self.assertFalse(self.talent.user.check_password(self.data["password"]))
