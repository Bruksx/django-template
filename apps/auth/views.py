from accounts.enums import SocialType
from accounts.models import User
from accounts.schemas import common as common_schema
from ninja import Router
from ninja.errors import HttpError

from helpers.utils import failure_response
from services import google, linkedin
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


@router.post("google/login", response=common_schema.UserSchema)
def google_login(request, data: GoogleAuthSchema):
    tokens = google.get_tokens(code=data.code)
    if not tokens:
        return failure_response(message= "Tokens not found", status=404)
    profile = google.get_profile_details(tokens.access_token)
    if not profile:
        return failure_response(message="Profile not found", status=404)
    user = handle_social_login(profile, data.user_type, SocialType.GOOGLE)
    validate_login(user)
    return user


@router.post("linkedin/login", response=common_schema.UserSchema)
def linkedin_login(request, data: LinkedInAuthSchema):
    tokens = linkedin.get_tokens(code=data.code)
    if not tokens:
        return failure_response(message= "Tokens not found", status=404)
    profile = linkedin.get_profile_details(tokens.access_token)
    if not profile:
        return failure_response(message="Profile not found", status=404)
    user = handle_social_login(profile, data.user_type, SocialType.LINKEDIN)
    validate_login(user)
    return user


@router.post('facebook/login', response=common_schema.UserSchema)
def facebook_login(request, data: FaceBookLoginSchema):
    fb_user = facebook_client.get_user(data.user_id, data.access_token)
    existing_user = User.objects.filter(facebook_id=fb_user.id, type=data.type).first()
    if existing_user:
        return existing_user
    else:
        new_user = User(
            first_name = fb_user.first_name,
            last_name = fb_user.last_name,
            email = fb_user.email,
            type = data.type.value,
        )
        #new_user.save()
        return new_user


