from copy import deepcopy

from django.db.models import Q
from django.utils import timezone
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from ninja.errors import HttpError
from ninja_jwt.exceptions import AuthenticationFailed

from config.settings import GOOGLE_CLIENT_ID
from helpers.email.auth import send_verification_code
from monkeypatches.q_cluster import async_task
from services.auth.schema import ProfileSchema
from services.auth.facebook import facebook_client

from accounts.enums import UserType, AuthType, SocialType, BusinessUserRoleType
from accounts.models import BusinessUser, VerificationCode, User, Talent, Business
from auth.enums import AuthActionEnum

from .client import LinkedInAPI
from .schema import SocialAuthSchema


def validate_login(user: User, raise_exception=True):
    try:
        if not user:
            raise HttpError(404, "You don't have an account with us")
        if not user.email_verified:
            verification_code = VerificationCode(email=user.email)
            raw_code = verification_code.save()
            async_task(send_verification_code, email=user.email, code=raw_code, user=user.fullname, company=None)
            raise HttpError(401, "Your email is not verified")
        if not user.is_active:
            raise HttpError(401, "Your account is not active")
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return True
    except HttpError as e:
        if raise_exception:
            raise e
        return False


def handle_social_login(data: SocialAuthSchema)->User:
    auth_mode = "login"
    if data.user_type:
        auth_mode = "register"
    profile_dict = {}

    if data.social_type == SocialType.GOOGLE:
        auth_type = AuthType.GOOGLE
        try:
            idinfo = id_token.verify_oauth2_token(
                data.access_token,
                grequests.Request(),
                GOOGLE_CLIENT_ID
            )
        except ValueError:
            raise HttpError(401, "Invalid Google token")
        
        profile_dict["google_id"] = idinfo["sub"]
        profile_dict["first_name"] = idinfo["given_name"]
        profile_dict["last_name"] = idinfo["family_name"]
        social_query = Q(google_id=idinfo["sub"])

    elif data.social_type == SocialType.LINKEDIN:
        api = LinkedInAPI()
        code = data.access_token
        access_token = api.get_access_token(code, data.redirect_uri)
        linkedin_profile = api.get_profile(access_token)
        auth_type = AuthType.LINKEDIN
        social_query = Q(linkedin_id=linkedin_profile.sub)
        profile_dict["linkedin_id"] = linkedin_profile.sub
        profile_dict["first_name"] = linkedin_profile.given_name
        profile_dict["last_name"] = linkedin_profile.family_name
        profile_dict["email"] = linkedin_profile.email

    elif data.social_type == SocialType.FACEBOOK:
        auth_type = AuthType.FACEBOOK
        user = facebook_client.get_user()
        profile_dict["first_name"] = user.first_name
        profile_dict["last_name"] = user.last_name
        profile_dict["facebook_id"] = user.id
        social_query = Q(facebook_id=user.id)

    elif SocialType.APPLE.value == data.social_type:
        pass
        """auth_type = AuthType.APPLE
        social_query = Q(apple_id=profile.id)
        profile_dict["apple_id"] = profile.id"""
    
    user = User.objects.filter(social_query).first()
    if user:
        if user.auth_mode == AuthType.EMAIL.value:
            raise AuthenticationFailed(detail="Kindly login through email and password")
        if user.auth_mode != auth_type.value:
            raise AuthenticationFailed(detail=f"Kindly login through {user.auth_mode} ")
        return user

    if auth_mode == "register" and not data.user_type:
        raise AuthenticationFailed(detail="Account not found! please create an account")
    
    user = User.objects.create_user(**profile_dict,
                                    type=data.user_type.value,
                                    email_verified=True, is_active=True,
                                    auth_mode=auth_type.value)
    if data.user_type == UserType.TALENT:
        Talent.objects.create(user=user)
    elif data.user_type == UserType.BUSINESS:
        business = Business.objects.create(created_by=user)
        BusinessUser.objects.create(user=user, role=BusinessUserRoleType.OWNER.value, business=business)
    return user