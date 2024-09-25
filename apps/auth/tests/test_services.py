import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.dtos import TokenDto
from accounts.enums import SocialType, UserType
from services.schema import ProfileSchema

from auth.services import google_auth_login

User = get_user_model()


class TestGoogleServiceTests(TestCase):

    def test_google_auth_login(self):
        profile = ProfileSchema(id=None, email="test@example.com",
                                first_name="Test", last_name="User")
        user_type = UserType.TALENT
        self.assertFalse(User.objects.filter(email__iexact=profile.email).exists())
        user = google_auth_login(profile, user_type)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.auth_mode, SocialType.GOOGLE.value)
