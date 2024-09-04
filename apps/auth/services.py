from ninja_jwt.exceptions import AuthenticationFailed
from ninja_jwt.tokens import RefreshToken

from accounts.dtos import TokenDto
from accounts.enums import SocialType, UserType, AuthType
from accounts.models import User
from services.schema import ProfileSchema


def login_social_user(profile: ProfileSchema, social_type: SocialType)->TokenDto:
    user = User.objects.filter(email__iexact=profile.email).first()
    if not user:
        raise AuthenticationFailed(detail="You have no account with us")
    if user.auth_mode == AuthType.EMAIL:
        raise AuthenticationFailed(detail="Kindly login through email and password")
    if user.auth_mode != social_type.value:
        raise  AuthenticationFailed(detail=f"Kindly login through {user.auth_mode} ")
    if not user.is_active:
        raise AuthenticationFailed(detail=f"You have been blocked")
    return user.tokens()


def create_social_user(profile: ProfileSchema, user_type: UserType, social_type: SocialType)->TokenDto:
    user = User.objects.filter(email__iexact=profile.email).first()
    if user:
        return login_social_user(profile, social_type)
    password = User.objects.make_random_password(length=10)
    user = User.objects.create_user(**profile.__dict__, password=password,
                                    type=user_type.value, auth_mode=social_type.value,
                                    is_active=True, email_verified=True)
    return user.tokens()

