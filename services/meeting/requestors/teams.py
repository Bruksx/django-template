import requests
from .base import BaseRequestor
import msal
from config.settings import TEAMS_CLIENT_ID, TEAMS_CLIENT_SECRET


class TeamsRequestor(BaseRequestor):
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.get_access_token()}"
        }
        self.TEAMS_TENANT_ID = "me"
        self.AUTHORITY = f"https://login.microsoftonline.com/{self.TEAMS_TENANT_ID}"
        self.SCOPES = ["https://graph.microsoft.com/.default"]
    
    def get_access_token(self):
        app = msal.ConfidentialClientApplication(
            TEAMS_CLIENT_ID, authority=self.AUTHORITY, client_credential=TEAMS_CLIENT_SECRET
        )
        result = app.acquire_token_for_client(scopes=self.SCOPES)
        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception("Could not obtain access token.")