from django.contrib.auth import get_user_model
from django.test import TestCase
from ninja.errors import HttpError
from ninja_extra.exceptions import ErrorDetail
from ninja_jwt.exceptions import AuthenticationFailed
from services.schema import ProfileSchema

from accounts.enums import SocialType, UserType, AuthType
from auth.enums import AuthActionEnum
from auth.services import handle_social_login, validate_login

User = get_user_model()


class TestHandleSocialLogin(TestCase):

    def test_signup_for_new_user(self):
        profile = ProfileSchema(id="12345", email="test@example.com",
                                first_name="Test", last_name="User")
        user_type = UserType.TALENT
        self.assertFalse(User.objects.filter(email__iexact=profile.email).exists())
        user = handle_social_login(profile, user_type, SocialType.GOOGLE, AuthActionEnum.SIGNUP)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.auth_mode, AuthType.GOOGLE.value)

    def test_login_for_existing_user(self):
        existing_user = User.objects.create_user(email="test@example.com",
                    password="securepassword", google_id="12345",  email_verified=True,
                    is_active=True, auth_mode=AuthType.GOOGLE.value)
        profile = ProfileSchema(id="12345", email="test@example.com",
                                first_name="Test", last_name="User")
        user_type = UserType.TALENT
        user = handle_social_login(profile, user_type, SocialType.GOOGLE, AuthActionEnum.LOGIN)
        self.assertIsNotNone(user)
        self.assertEqual(user, existing_user)


    def test_login_for_user_with_email_auth_mode(self):
        User.objects.create_user(email="test@example.com",
                                 password="securepassword", email_verified=True,
                                 is_active=True, auth_mode=AuthType.EMAIL.value)
        profile = ProfileSchema(id="12345", email="test@example.com",
                                first_name="Test", last_name="User")
        user_type = UserType.TALENT
        with self.assertRaises(AuthenticationFailed) as context:
            handle_social_login(profile, user_type, SocialType.GOOGLE, AuthActionEnum.LOGIN)
        self.assertEqual(context.exception.detail.get("detail"),
         ErrorDetail(string="User was not found with this social account", code=""))

    def test_login_for_user_with_different_auth_mode(self):
        User.objects.create_user(email="test@example.com",
                                 password="securepassword",facebook_id="12345", email_verified=True,
                                 is_active=True, auth_mode=AuthType.FACEBOOK)
        profile = ProfileSchema(id="12345", email="test@example.com",
                                first_name="Test", last_name="User")
        user_type = UserType.TALENT
        with self.assertRaises(AuthenticationFailed) as context:
            handle_social_login(profile, user_type, SocialType.GOOGLE, AuthActionEnum.LOGIN)
        self.assertEqual(context.exception.detail.get("detail"),
                         ErrorDetail(string="User was not found with this social account", code=""))

    def test_signup_for_existing_user(self):
        User.objects.create_user(email="test@example.com", google_id="12345",
                                 password="securepassword", email_verified=True,
                                 is_active=True, auth_mode=AuthType.GOOGLE.value)
        profile = ProfileSchema(id="12345", email="test@example.com",
                                first_name="Test", last_name="User")
        user_type = UserType.TALENT
        user = handle_social_login(profile, user_type, SocialType.GOOGLE, AuthActionEnum.SIGNUP)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.auth_mode, AuthType.GOOGLE.value)

class TestValidateLogin(TestCase):


    def test_for_existing_user(self):
        user = User.objects.create_user(email="test@example.com", google_id="12345",
                                 password="securepassword", email_verified=True,
                                 is_active=True, auth_mode=AuthType.GOOGLE.value)

        valid = validate_login(user, raise_exception=False)
        self.assertTrue(valid)

    def test_for_unverified_email_user(self):
        user = User.objects.create_user(email="test@example.com", google_id="12345",
                                 password="securepassword", email_verified=False,
                                 is_active=True, auth_mode=AuthType.GOOGLE.value)

        with self.assertRaises(HttpError) as context:
            validate_login(user)
        self.assertEqual(context.exception.message, "Your email is not verified")
        self.assertEqual(context.exception.status_code, 401)

    def test_for_blocked_user(self):
        user = User.objects.create_user(email="test@example.com", google_id="12345",
                                 password="securepassword", email_verified=True,
                                 is_active=False, auth_mode=AuthType.GOOGLE.value)

        with self.assertRaises(HttpError) as context:
            validate_login(user)
        self.assertEqual(context.exception.message, "Your account is not active")
        self.assertEqual(context.exception.status_code, 401)
