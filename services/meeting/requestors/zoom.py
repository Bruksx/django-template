import requests
from config.settings import ZOOM_CLIENT_SECRET

class ZoomRequestor:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ZOOM_CLIENT_SECRET}"
        }
    def get(self, url, params="", payload={}) -> requests.models.Response:
        return requests.get(url, params=params, headers=self.headers, json=payload)
    
    def post(self, url, params="", payload={}) -> requests.models.Response:
        return requests.post(url, params=params, headers=self.headers, json=payload)