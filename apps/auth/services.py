import logging
from copy import deepcopy

from django.db.models import Q
from ninja.errors import HttpError
from ninja_jwt.exceptions import AuthenticationFailed
from services.schema import ProfileSchema

from accounts.enums import UserType, AuthType, SocialType
from accounts.models import BusinessUser
from accounts.models import User, Talent
from auth.enums import AuthActionEnum


def validate_login(user: User, raise_exception=True):
    try:
        if not user:
            raise HttpError(404, "You don't have an account with us")
        if not user.email_verified:
            # TODO: Send verification email to user
            raise HttpError(401, "Your email is not verified")
        if not user.is_active:
            raise HttpError(401, "Your account is not active")
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
        auth_type = AuthType.LINKEDIN
        social_query = Q(linkedin_id=profile.id)
        profile_dict["linkedin_id"] = profile.id
    elif SocialType.FACEBOOK == social_type:
        auth_type = AuthType.FACEBOOK
        social_query = Q(facebook_id=profile.id)
        profile_dict["facebook_id"] = profile.id
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

    if action == AuthActionEnum.PROFILE:
        raise AuthenticationFailed(detail="User was not found with this social account")

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