from copy import deepcopy
import requests
import json
import jwt
from jwt.exceptions import DecodeError
from urllib.parse import quote, urlencode
import time

from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import get_random_string
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from ninja.errors import HttpError
from ninja_jwt.exceptions import AuthenticationFailed
from requests.exceptions import HTTPError as RequestsError

from config.settings import GOOGLE_CLIENT_ID, APPLE_CONFIG
from helpers.email.auth import send_verification_code
from monkeypatches.q_cluster import async_task
from services.auth.schema import ProfileSchema
from services.auth.facebook import Facebook

from accounts.enums import UserType, AuthType, SocialType, BusinessUserRoleType
from accounts.models import BusinessUser, VerificationCode, User, Talent, Business
from core.services import get_settings
from django.db.models import Q
from django.utils import timezone
from google.auth.transport import requests as grequests
from google.oauth2 import id_token
from ninja.errors import HttpError

from helpers.email.auth import send_verification_code
from monkeypatches.q_cluster import async_task
from services.auth.facebook import Facebook
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
    


class AppleAuth:
    RESPONSE_TYPE = "code"

    def __init__(self, code=None, response_handler=None):
        self.code = code
        self.response_handler = response_handler
        self.APPLE_ACCESS_TOKEN_URL = "https://appleid.apple.com/auth/token"
        self.APPLE_KEY_ID = APPLE_CONFIG["APPLE_KEY_ID"]
        self.APPLE_CLIENT_ID = APPLE_CONFIG["APPLE_CLIENT_ID"]
        self.APPLE_REDIRECT_URL = APPLE_CONFIG["APPLE_REDIRECT_URL"]
        self.APPLE_TEAM_ID = APPLE_CONFIG["APPLE_TEAM_ID"]
        self.APPLE_CLIENT_ID = APPLE_CONFIG["APPLE_CLIENT_ID"]
        self.APPLE_PRIVATE_KEY = APPLE_CONFIG["APPLE_PRIVATE_KEY"]

    def get_state(self, redirect_url, extra_state):
        identifier = get_random_string(128)
        state = {
            "identifier": identifier,
            self.FE_REDIRECT_URL_PARAM: redirect_url,
        }

        if extra_state:
            extra_state = json.loads(extra_state)
            state.update(extra_state)

        state = json.dumps(state)
        return state

    def get_auth_params(self, state=None):
        scope = "name email"

        params = {
            "client_id": self.APPLE_CLIENT_ID,
            "redirect_uri": self.APPLE_REDIRECT_URL,
        }

        if state:
            params["state"] = state

        if scope:
            params["scope"] = " ".join(scope)

        if self.RESPONSE_TYPE:
            params["response_type"] = self.RESPONSE_TYPE

        params["response_mode"] = "form_post"

        params = urlencode(params, quote_via=quote)
        return params

    def do_auth(self):
        response_data = {}
        client_secret = self.get_client_secret()
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": self.APPLE_CLIENT_ID,
            "client_secret": client_secret,
            "code": self.code,
            "grant_type": "authorization_code",
        }
        apple_response = requests.post(
            self.APPLE_ACCESS_TOKEN_URL, data=data, headers=headers
        )
        response_dict = apple_response.json()
        id_token = response_dict.get("id_token", None)
        if id_token:
            decoded = jwt.decode(id_token, "secret", verify=False)
            response_data.update(
                {"email": decoded["email"]}
            ) if "email" in decoded else None
            response_data.update(
                {"apple_id": decoded["sub"]}
            ) if "sub" in decoded else None
        return response_data

    def get_user_details(self, request, response_dict):
        return self.response_handler.handle_fetch_or_create_user(request, response_dict)
    
    def apple_exchange_code(self):
        """data = {
            "client_id": self.APPLE_CLIENT_ID,
            "client_secret": self.get_client_secret(),
            "code": self.code,
            "grant_type": "identity_token",
        }
        headers = {"content-type": "application/x-www-form-urlencoded"}
        r = requests.post("https://appleid.apple.com/auth/token", data=data, headers=headers)"""
        """print(r.json())
        r.raise_for_status()
        response_data = r.json()"""
        try:
            data = self.decode_token(self.code)
            if data.get("iss") != "https://appleid.apple.com":
                raise HttpError(400, "Invalid Login")
            now = time.time()
            exp = data.get("exp")
            """if exp:
                if exp > now:
                    raise HttpError(400, "Invalid Login")"""
            return data 
        except:
            raise HttpError(400, "Invalid Login")
        
    def verify_token(self):
        header = jwt.get_unverified_header(self.code)
        kid = header["kid"]
        jwks = requests.get("https://appleid.apple.com/auth/keys").json()

        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if not public_key:
            raise Exception("No matching Apple public key found")

        try:
            payload = jwt.decode(
                self.code,
                public_key,
                algorithms=["RS256"],
                audience=self.APPLE_CLIENT_ID
            )
            print(payload)
        except jwt.ExpiredSignatureError:
            print("Apple token expired")
        except jwt.InvalidTokenError as e:
            print("Invalid Apple token:", e)


    def get_client_secret(self):
        headers = {"kid": self.APPLE_KEY_ID}
        TOKEN_TTL = 500
        now = int(time.time())
        payload = {
            "iss": self.APPLE_TEAM_ID,
            "iat": now,
            "exp": now + TOKEN_TTL,
            "aud": "https://appleid.apple.com",
            "sub": self.APPLE_CLIENT_ID,
        }
        client_secret = jwt.encode(
            payload,
            key=self.APPLE_PRIVATE_KEY,
            algorithm="ES256",
            headers=headers,
        )
        return client_secret

    def ios_auth(self, id_token):
        response_data = {}
        if id_token:
            decoded = jwt.decode(id_token, "secret", verify=False)
            response_data.update(
                {"email": decoded["email"]}
            ) if "email" in decoded else None
            response_data.update(
                {"apple_id": decoded["sub"]}
            ) if "sub" in decoded else None
        return response_data

    def decode_token(self, token):
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload




def handle_social_login(data: SocialAuthSchema)->User:
    settings = get_settings()
    error_message = "This login method is currently unavailable. Please try another option."
    if not settings.social_auth:
        raise HttpError(400, error_message)
    auth_mode = "login"
    if data.user_type:
        auth_mode = "register"
    profile_dict = {}

    if data.social_type == SocialType.GOOGLE:
        if not settings.google_auth:
            raise HttpError(400, error_message)
        auth_type = AuthType.GOOGLE
        try:
            idinfo = id_token.verify_firebase_token(
                data.access_token,
                grequests.Request(),
            )
        except Exception as e:
            idinfo = id_token.verify_oauth2_token(
                data.access_token,
                grequests.Request(),
                data.app_id,
            )
        except:
            raise HttpError(401, "Invalid Google token")
        first_name, last_name = idinfo["name"].split()
        profile_dict["email"] = idinfo["email"]
        profile_dict["google_id"] = idinfo["sub"]
        profile_dict["first_name"] = first_name
        profile_dict["last_name"] = last_name
        social_query = Q(email=idinfo["email"])

    elif data.social_type == SocialType.LINKEDIN:
        if not settings.linkedin_auth:
            raise HttpError(400, error_message)
        api = LinkedInAPI()
        code = data.access_token
        access_token = api.get_access_token(code, data.redirect_uri)
        linkedin_profile = api.get_profile(access_token)
        auth_type = AuthType.LINKEDIN
        social_query = Q(email=linkedin_profile.email)
        profile_dict["linkedin_id"] = linkedin_profile.sub
        profile_dict["first_name"] = linkedin_profile.given_name
        profile_dict["last_name"] = linkedin_profile.family_name
        profile_dict["email"] = linkedin_profile.email

    elif data.social_type == SocialType.FACEBOOK:
        if not settings.facebook_auth:
            raise HttpError(400, error_message)
        auth_type = AuthType.FACEBOOK
        facebook_client = Facebook()
        user = facebook_client.get_user(data.social_id, data.access_token)
        profile_dict["first_name"] = user.first_name
        profile_dict["last_name"] = user.last_name
        profile_dict["facebook_id"] = user.id
        profile_dict["email"] = user.email
        social_query = Q(email=user.email)

    elif data.social_type == SocialType.APPLE:
        if not settings.social_auth:
            raise HttpError(400, error_message)
        code = data.access_token
        apple_auth = AppleAuth(code=code)
        try:
            user_data = apple_auth.apple_exchange_code()
            print(user_data)
        except RequestsError:
            raise HttpError(400, "invalid login")
        auth_type = AuthType.APPLE
        profile_dict["apple_id"] = user_data["sub"]
        profile_dict["first_name"] = data.first_name
        profile_dict["last_name"] = data.last_name
        profile_dict["email"] = user_data["email"]
        social_query = Q(email=user_data["email"])
    
    user = User.objects.filter(social_query).first()
    if user:
        if user.auth_mode == AuthType.EMAIL.value:
            raise HttpError(403, "Kindly login through email and password")
        if user.auth_mode != auth_type.value:
            raise HttpError(403, f"Kindly login through {user.auth_mode}")
        return user

    if auth_mode == "login" and not data.user_type:
        raise HttpError(403, "Account not found! please create an account")
    
    existing_user = User.objects.filter(email=profile_dict["email"]).exists()
    if existing_user:
        raise HttpError(403, "An account already exists with this email")
    user = User(**profile_dict,
                type=data.user_type.value,
                email_verified=True, is_active=True,
                auth_mode=auth_type.value
            )
    user.__is_new = True
    user.save()

    if data.user_type == UserType.TALENT:
        Talent.objects.create(user=user)
    elif data.user_type == UserType.BUSINESS:
        business = Business.objects.create(created_by=user)
        BusinessUser.objects.create(user=user, role=BusinessUserRoleType.OWNER.value, business=business,
                                    default_sender_email=user.email)
    return user
