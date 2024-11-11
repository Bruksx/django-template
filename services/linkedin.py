from json import JSONDecodeError
from typing import Optional
from urllib.parse import urlencode

import requests
from django.conf import settings

from helpers.loggers import Logger
from services.schema import FreshTokenSchema, TokenSchema, ProfileSchema

LINKEDIN_CLIENT_ID = settings.LINKEDIN_CLIENT_ID
LINKEDIN_CLIENT_SECRET = settings.LINKEDIN_CLIENT_SECRET
LINKEDIN_REDIRECT_URI = settings.LINKEDIN_REDIRECT_URI


def get_authorization_url()->str:
    return "https://www.linkedin.com/oauth/v2/authorization?"\
            + urlencode({
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "scope": "r_liteprofile r_emailaddress",
    })


# Step 2: Handle the callback from LinkedIn
def get_tokens(code: str)->Optional[FreshTokenSchema|TokenSchema]:
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }

    response = requests.post(token_url, data=token_data)
    try:
        response_data = response.json()
        if "refresh_token" in response_data:
            return FreshTokenSchema(
                **response_data
            )
        elif "access_token" in response_data:
            return TokenSchema(**response_data)
        else:
            Logger.error(dict(
                sender="LinkedIn service",
                title="LinkedIn Token Error",
                description=f"access token not found: {response}"
            ))
            return None
    except JSONDecodeError as e:
        Logger.error(dict(
            sender="LinkedIn service",
            title="LinkedIn Token Error",
            description=str(e)
        ))
        return None



def refresh_tokens(refresh_token: str)->Optional[FreshTokenSchema|TokenSchema]:
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }

    response = requests.post(token_url, data=token_data)
    try:
        response_data = response.json()
        if "refresh_token" in response_data:
            return FreshTokenSchema(
                **response_data
            )
        elif "access_token" in response_data:
            return TokenSchema(**response_data)
        else:
            Logger.error(dict(
                sender="LinkedIn service",
                title="LinkedIn Token Error",
                description=f"access token not found: {response}"
            ))
            return None
    except JSONDecodeError as e:
        Logger.error(dict(
            sender="LinkedIn service",
            title="LinkedIn Token Error",
            description=str(e)
        ))
        return None




def get_profile_details(access_token:str)->Optional[ProfileSchema]:
    profile_url = "https://api.linkedin.com/v2/me"
    email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    try:
        profile_response = requests.get(profile_url, headers=headers).json()
        email_response = requests.get(email_url, headers=headers).json()
        return ProfileSchema(
            email= email_response['elements'][0]['handle~']['emailAddress'],
            first_name= profile_response.get("localizedFirstName"),
            last_name=  profile_response.get("localizedLastName"),
            id= profile_response.get("id"),
        )
    except Exception as e:
        Logger.error(dict(
            sender="LinkedIn service",
            title="LinkedIn Profile Error",
            description=str(e)
        ))
        return None