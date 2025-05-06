import pyfacebook
import requests
from ninja.errors import HttpError
from pyfacebook import GraphAPI, FacebookApi
from pyfacebook.exceptions import FacebookError

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
    def __init__(self, APP_ID, ):
        self.APP_ID = APP_ID
        self.APP_SECRET = APP_MAP[APP_ID]
        try:
            self.api = GraphAPI(app_id=self.APP_ID, app_secret=self.APP_SECRET, application_only_auth=True)
        except (pyfacebook.exceptions.FacebookError,
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout):
            pass

    def get_login_url(self):
        api = GraphAPI(app_id=self.APP_ID, app_secret=self.APP_SECRET, oauth_flow=True)
        url, _ = api.get_authorization_url(redirect_uri="https://127.0.0.1:8000/api/auth/facebook/redirect")
        return url
    
    def get_user(self, user_id, access_token):
        fb_api = FacebookApi(app_id=self.APP_ID, app_secret=self.APP_SECRET, access_token=access_token)
        try:
            return fb_api.user.get_info(user_id)
        except FacebookError as e:
            raise HttpError(403, e.message)


#facebook_client = Facebook(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)