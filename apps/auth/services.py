from copy import deepcopy

from django.db.models import Q
from django.utils import timezone
from ninja.errors import HttpError
from ninja_jwt.exceptions import AuthenticationFailed

from helpers.email.auth import send_verification_code
from monkeypatches.q_cluster import async_task
from services.auth.schema import ProfileSchema

from accounts.enums import UserType, AuthType, SocialType
from accounts.models import BusinessUser, VerificationCode
from accounts.models import User, Talent
from auth.enums import AuthActionEnum

from .client import LinkedInAPI


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


def handle_social_login(profile: ProfileSchema, user_type: UserType, social_type: SocialType, action: AuthActionEnum)->User:
    profile_dict = deepcopy(profile.__dict__)
    profile_dict.pop("id", None)

    if SocialType.GOOGLE == social_type:
        auth_type = AuthType.GOOGLE
        social_query = Q(google_id=profile.id)
        profile_dict["google_id"] = profile.id

    elif SocialType.LINKEDIN == social_type:
        api = LinkedInAPI()
        code = profile.id
        access_token = api.get_access_token(code)
        linkedin_profile = api.get_profile(access_token)
        auth_type = AuthType.LINKEDIN
        social_query = Q(linkedin_id=linkedin_profile.id)
        profile_dict["linkedin_id"] = profile.id
        profile_dict["first_name"] = linkedin_profile.firstName
        profile_dict["last_name"] = linkedin_profile.lastName

    elif SocialType.FACEBOOK == social_type:
        auth_type = AuthType.FACEBOOK
        social_query = Q(facebook_id=profile.id)
        profile_dict["facebook_id"] = profile.id
    elif SocialType.APPLE == social_type:
        auth_type = AuthType.APPLE
        social_query = Q(apple_id=profile.id)
        profile_dict["apple_id"] = profile.id
    else:
        raise HttpError(400, "Invalid social type")
    user = User.objects.filter(social_query).first()
    if user:
        if user.auth_mode == AuthType.EMAIL.value:
            raise AuthenticationFailed(detail="Kindly login through email and password")
        if user.auth_mode != auth_type.value:
            raise AuthenticationFailed(detail=f"Kindly login through {user.auth_mode} ")
        return user
    if action == AuthActionEnum.LOGIN:
        raise AuthenticationFailed(detail="User was not found with this social account")
    if not profile.first_name  or not profile.email:
        raise HttpError(400, "First name and email are required")
    password = User.objects.make_random_password()
    user = User.objects.create_user(**profile_dict,
                                    password=password,
                                    type=user_type.value,
                                    email_verified=True, is_active=True,
                                    auth_mode=auth_type.value)
    if user_type == UserType.TALENT:
        Talent.objects.create(user=user)
    elif user_type == UserType.BUSINESS:
        BusinessUser.objects.create(user=user)
    return user

"""
def linkedin_auth(request, data: LinkedInAuthSchema):
    tokens = linkedin.get_tokens(code=data.code)
    if not tokens:
        return failure_response(message= "Tokens not found", status=404)
    profile = linkedin.get_profile_details(tokens.access_token)
    if not profile:
        return failure_response(message="Profile not found", status=404)
    user = handle_social_login(profile, data.user_type, SocialType.LINKEDIN, data.action)
    validate_login(user)
    return user
    
"""