from django.db.models import Q
from ninja.errors import HttpError
from ninja_jwt.exceptions import AuthenticationFailed
from services.schema import ProfileSchema

from accounts.enums import UserType, AuthType, SocialType
from accounts.models import BusinessUser
from accounts.models import User, Talent



def validate_login(user: User):
    if not user:
        raise HttpError(404, "You don't have an account with us")
    if not user.email_verified:
        #TODO: Send verification email to user
        raise HttpError(401, "Your email is not verified")
    if not user.is_active:
        raise HttpError(401, "Your account is not active")
    return

def handle_social_login(profile: ProfileSchema, user_type: UserType, social_type: SocialType)->User:
    profile_dict = profile.__dict__
    profile_dict.pop("id", None)

    if SocialType.GOOGLE == social_type:
        auth_type = AuthType.GOOGLE
        social_query = Q(google_id=profile.id)
        profile_dict["google_id"] = profile.id

    elif SocialType.LINKEDIN == social_type:
        auth_type = AuthType.LINKEDIN
        social_query = Q(linkedin_id=profile.id)
        profile_dict["linkedin_id"] = profile.id
    else:
        raise HttpError(400, "Invalid social type")
    user = User.objects.filter(social_query).first()
    if user:
        return user
    user = User.objects.filter(email__iexact=profile.email).first()
    if user:
        if user.auth_mode == AuthType.EMAIL:
            raise AuthenticationFailed(detail="Kindly login through email and password")
        elif user.auth_mode != auth_type.value:
            raise AuthenticationFailed(detail=f"Kindly login through {user.auth_mode} ")
        return user
    password = User.objects.make_random_password()
    user = User.objects.create_user(**profile_dict,
                                    password=password,
                                    type=user_type.value,
                                    email_verified=True, is_active=True,
                                    auth_mode=social_type.value)
    if user_type == UserType.TALENT:
        Talent.objects.create(user=user)
    elif user_type == UserType.BUSINESS:
        BusinessUser.objects.create(user=user)
    return user