import logging
from typing import Optional

import requests
from django.conf import settings
from requests import JSONDecodeError

from services.schema import FreshTokenSchema, TokenSchema, ProfileSchema

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI



def get_authorization_url()->str:
    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
    return f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope={scope}&access_type=offline"


def get_tokens(code:str)->Optional[FreshTokenSchema|TokenSchema]:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }
    )
    try:
        response_data = response.json()
        if "refresh_token" in response_data:
            return FreshTokenSchema(
                access_token=response_data["access_token"],
                expires_in=response_data["expires_in"],
                scope=response_data["scope"],
                refresh_token=response_data["refresh_token"]
            )
        elif "access_token" in response_data:
            return TokenSchema(
                access_token=response_data["access_token"],
                expires_in=response_data["expires_in"],
                scope=response_data["scope"]
            )
        else:
            logging.critical(f"Gmail Token Error: access token not found: {response}", )
            return None
    except JSONDecodeError as e:
        logging.critical(f"Gmail Token Error: {e}")
        return None



def refresh_tokens(refresh_token:str)->Optional[FreshTokenSchema|TokenSchema]:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            'refresh_token': refresh_token,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'refresh_token',
        }
    )
    try:
        response_data = response.json()
        if "refresh_token" in response_data:
            return FreshTokenSchema(
                access_token=response_data["access_token"],
                expires_in=response_data["expires_in"],
                scope=response_data["scope"],
                refresh_token=response_data["refresh_token"]
            )
        elif "access_token" in response_data:
            return TokenSchema(
                access_token=response_data["access_token"],
                expires_in=response_data["expires_in"],
                scope=response_data["scope"]
            )
        else:
            logging.critical(f"Gmail Token Error: access token not found: {response}", )
            return None
    except JSONDecodeError as e:
        logging.critical(f"Gmail Token Error: {e}")
        return None

def get_profile_details(access_token:str)->Optional[ProfileSchema]:
    user_info_response = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        params={'access_token': access_token}
    )
    user_info = user_info_response.json()
    name = user_info.get("name").split(" ")
    return ProfileSchema(
        email=user_info.get("email").lower(),
        first_name=name[0].title(),
        last_name=" ".join(name[1: ]).title()
    )






