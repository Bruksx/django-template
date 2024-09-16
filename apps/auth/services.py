from ninja.errors import HttpError
from ninja_jwt.exceptions import AuthenticationFailed
from services.schema import ProfileSchema

from accounts.enums import UserType, AuthType
from accounts.models import BusinessUser
from accounts.models import User, Talent


def google_auth_login(profile: ProfileSchema, user_type: UserType)->User:
    user = User.objects.filter(google_id=profile.id).first()
    if user:
        return user
    user = User.objects.filter(email__iexact=profile.email).first()
    if user:
        if user.auth_mode == AuthType.EMAIL:
            raise AuthenticationFailed(detail="Kindly login through email and password")
        elif user.auth_mode != AuthType.GOOGLE:
            raise AuthenticationFailed(detail=f"Kindly login through {user.auth_mode} ")
        return user
    password = User.objects.make_random_password()
    user = User.objects.create_user(**profile.__dict__,
                                    password=password,
                                    type=user_type.value,
                                    email_verified=True, is_active=True)
    if user_type == UserType.TALENT:
        Talent.object.create(user=user)
    elif user_type == UserType.BUSINESS:
        BusinessUser.objects.create(user=user)
    return user

def validate_login(user: User):
    if not user:
        raise HttpError(404, "You don't have an account with us")
    if not user.email_verified:
        #TODO: Send verification email to user
        raise HttpError(401, "Your email is not verified")
    if not user.is_active:
        raise HttpError(401, "Your account is not active")
    return
