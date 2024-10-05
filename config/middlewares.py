import logging
from urllib.parse import parse_qsl

from django.contrib.auth.models import AnonymousUser
from ninja_jwt.tokens import RefreshToken

from helpers.utils import is_valid_uuid


class QueryAuthMiddleware:
    def __init__(self, app):
        self.app = app

    def get_user_with_uid(self, user_id):
        from accounts.models import User
        return User.objects.filer(uid=user_id).first()

    def get_user_with_token(self, token:str):
        from accounts.models import User
        payload = RefreshToken(token).payload
        user_id = payload.get("user_id")
        if not user_id:
            return
        return User.objects.filer(id=user_id).first()


    def __call__(self, scope, receive, send):
        user = AnonymousUser
        query_params = dict()
        logging.critical(f"query_params: {query_params}")
        query_string = str(scope["query_string"].decode())
        if query_string:
            query_params = dict(parse_qsl(query_string))
        if "user_id" in query_params:
            user_id = query_params.get("user_id")
            if user_id and is_valid_uuid(user_id):
                user = self.get_user(user_id) | AnonymousUser
            scope["user"] = user
        elif "token" in query_params:
            # a more secure approach
            token = query_params.get("token")
            user = self.get_user_with_token(token) | AnonymousUser
            scope["user"] = user

        return self.app(scope, receive, send)
