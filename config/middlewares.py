import logging
from urllib.parse import parse_qsl

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from ninja_jwt.authentication import JWTBaseAuthentication

from helpers.utils import is_valid_uuid


class QueryAuthMiddleware:
    def __init__(self, app):
        self.app = app

    @database_sync_to_async
    def get_user_with_uid(self, user_id):
        from accounts.models import User
        return User.objects.filter(uid=user_id).first()

    @database_sync_to_async
    def get_user_with_token(self, token:str):
        # more secured approach
        jwt  = JWTBaseAuthentication()
        token = jwt.get_validated_token(token)
        user = jwt.get_user(token)
        if not user:
            return
        return user


    async def __call__(self, scope, receive, send):
        user = AnonymousUser
        query_params = dict()
        query_string = str(scope["query_string"].decode())
        if query_string:
            query_params = dict(parse_qsl(query_string))
        if "user_id" in query_params:
            user_id = query_params.get("user_id")
            if user_id and is_valid_uuid(user_id):
                user = await self.get_user_with_uid(user_id) or AnonymousUser
            scope["user"] = user
        elif "token" in query_params:
            # a more secure approach
            token = query_params.get("token")
            user = await self.get_user_with_token(token) or AnonymousUser
            scope["user"] = user
        return await self.app(scope, receive, send)
