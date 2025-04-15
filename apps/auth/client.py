import requests
from config.settings import LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI
from .schema import LinkedInProfile
from dacite import from_dict


class LinkedInAPI:
    AUTH_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    PROFILE_URL = "https://api.linkedin.com/v2/me"
    EMAIL_URL = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"

    def __init__(self):
        self.client_id = LINKEDIN_CLIENT_ID
        self.client_secret = LINKEDIN_CLIENT_SECRET
        self.redirect_uri = LINKEDIN_REDIRECT_URI

    def get_access_token(self, code):
        """Exchange authorization code for access token"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = requests.post(self.AUTH_URL, data=data)
        response.raise_for_status()
        return response.json().get("access_token")

    def get_profile(self, access_token) -> LinkedInProfile:
        """Fetch basic profile data"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(self.PROFILE_URL, headers=headers)
        response.raise_for_status()
        return from_dict(LinkedInProfile, response.json())

    def get_email(self, access_token):
        """Fetch primary email address"""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(self.EMAIL_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["elements"][0]["handle~"]["emailAddress"]
