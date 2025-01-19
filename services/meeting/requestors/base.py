import requests


class BaseRequestor:
    def __init__(self):
        self.headers = {}

    def get(self, url, params="", payload={}) -> requests.models.Response:
        return requests.get(url, params=params, headers=self.headers, json=payload)
    
    def post(self, url, params="", payload={}) -> requests.models.Response:
        return requests.post(url, params=params, headers=self.headers, json=payload)