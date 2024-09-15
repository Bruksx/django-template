import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.dtos import TokenDto
from accounts.enums import SocialType, UserType
from auth.services import create_social_user, login_social_user
from services.schema import ProfileSchema

User = get_user_model()


class TestSocialAuthServicesTests(TestCase):

    def test_social_signup(self):
        profile = ProfileSchema(email="test@example.com",
                                first_name="Test", last_name="User")
        social_type = SocialType.GOOGLE
        user_type = UserType.TALENT
        self.assertFalse(User.objects.filter(email__iexact=profile.email).exists())
        token = create_social_user(profile, user_type, social_type)
        user = User.objects.filter(email__iexact=profile.email).first()
        self.assertTrue(isinstance(token, TokenDto))
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.auth_mode, SocialType.GOOGLE.value)


    def test_social_login(self):
        profile = ProfileSchema(email="test@gmail.com",
                                first_name="Test", last_name="User")
        social_type = SocialType.GOOGLE
        user_type = UserType.TALENT
        create_social_user(profile, user_type, social_type)
        token = login_social_user(profile, social_type)
        self.assertTrue(isinstance(token, TokenDto))

