import requests
from config.settings import ZOOM_CLIENT_SECRET
from .base import BaseRequestor


class ZoomRequestor(BaseRequestor):
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ZOOM_CLIENT_SECRET}"
        }