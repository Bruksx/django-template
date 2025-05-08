import pyfacebook
import requests
from ninja.errors import HttpError
from pyfacebook import GraphAPI, FacebookApi
from pyfacebook.exceptions import FacebookError
from dacite import from_dict
from apps.auth.schema import FacebookUser

from config.settings import (
    FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_APP_ID_ANDROID, FACEBOOK_APP_SECRET_ANDROID, FACEBOOK_APP_ID_IOS,
    FACEBOOK_APP_SECRET_IOS, FACEBOOK_APP_ID_WEB, FACEBOOK_APP_SECRET_WEB
)

APP_MAP = {
    FACEBOOK_APP_ID_ANDROID: FACEBOOK_APP_SECRET_ANDROID,
    FACEBOOK_APP_ID_IOS: FACEBOOK_APP_SECRET_IOS,
    FACEBOOK_APP_ID_WEB: FACEBOOK_APP_SECRET_WEB
}


class Facebook():
    def __init__(self, APP_ID):
        self.APP_ID = APP_ID
        self.APP_SECRET = APP_MAP[APP_ID]
        self.scope = ['email',]

    def get_user(self, user_id, access_token):
        url = f"https://graph.facebook.com/v18.0/me"
        params = {
            "fields": "id,name,email,first_name,last_name",
            "access_token": access_token
        }
        response = requests.get(url=url, params=params)
        user = from_dict(FacebookUser, response.json())
        return user



#facebook_client = Facebook(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)