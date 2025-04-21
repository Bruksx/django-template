import requests
from urllib3 import request

BASE_URL = "https://apis.indeed.com"

AUTH_URL = f"{BASE_URL}/oauth/v2/tokens"
GRAPHQL_URL = f"{BASE_URL}/graphql"

class IndeedJobPostingService:

    def __init__(self):
        ...

    def get_access_token(self):
        headers = {

        }
        response = requests.post(AUTH_URL, )
