from accounts.enums import SocialType
from accounts.models import User
from accounts.schemas import common as common_schema
from ninja import Router
from ninja.errors import HttpError

from helpers.utils import failure_response
from services import google, linkedin
from services.schema import ProfileSchema
from services.facebook import facebook_client
from auth.schema import LoginSchema, GoogleAuthSchema, FaceBookLoginSchema, LinkedInAuthSchema
from auth.services import handle_social_login, validate_login

# Create your views here.
router = Router(tags=["Auth"])


@router.post("login", response=common_schema.UserSchema)
def login(request, data:LoginSchema):
    user = User.objects.filter(email=data.email).first()
    validate_login(user)
    if not user.check_password(data.password):
        raise HttpError(401, "Invalid login credentials")
    return user


@router.post("google", response=common_schema.UserSchema)
def google_auth(request, data: GoogleAuthSchema):
    tokens = google.get_tokens(code=data.code)
    if not tokens:
        return failure_response(message="Tokens not found", status=404)
    profile = google.get_profile_details(tokens.access_token)
    if not profile:
        return failure_response(message="Profile not found", status=404)
    user = handle_social_login(profile, data.user_type, SocialType.GOOGLE, data.action)
    validate_login(user)
    return user


@router.post("linkedin", response=common_schema.UserSchema)
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


@router.post('facebook', response=common_schema.UserSchema)
def facebook_auth(request, data: FaceBookLoginSchema):
    fb_user = facebook_client.get_user(data.user_id, data.access_token)
    if not fb_user:
        return failure_response(message="Profile not found", status=404)
    profile = ProfileSchema(id=fb_user.id, email=fb_user.email, first_name=fb_user.first_name, last_name=fb_user.last_name)
    user = handle_social_login(profile, data.user_type, SocialType.FACEBOOK, data.action)
    validate_login(user)
    return user
