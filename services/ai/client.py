import requests

from config.settings import AI_SERVICE_BASE_URL


class GtcAiClient:
    def __init__(self):
        self.base_url = AI_SERVICE_BASE_URL
        self.timeout = 30
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path.lstrip('/')}"

    def get(self, path: str, params: dict = None):
        url = self._build_url(path)
        response = self.session.get(url, params=params, timeout=self.timeout)
        self._raise_for_status(response)
        return response

    def post(self, path: str, params: dict = None, json: dict=None):
        url = self._build_url(path)
        response = self.session.post(url, json=json, timeout=self.timeout, params=params)
        self._raise_for_status(response)
        return response

    def _raise_for_status(self, response):
        if not response.ok:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise Exception(
                f"API request failed ({response.status_code}): {detail}"
            )