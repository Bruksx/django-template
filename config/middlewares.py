import logging
import time
from datetime import datetime, timezone
from datetime import timedelta
from urllib.parse import parse_qsl

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.utils import timezone as django_timezone
from ninja_jwt.authentication import JWTBaseAuthentication

from helpers.loggers import Logger, LogSchema
from helpers.utils import is_valid_uuid

TTL = 60 * 60 * 24 * 2  # 2 days
ACTIVE_KEYS_KEY = "metrics:active_keys"


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


from django.db import close_old_connections

class DatabaseConnectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request (view execution, including any transaction.atomic)
        response = self.get_response(request)

        # After the view: Close all connections or old connections
        try:
            close_old_connections()  # Preferred: Closes only stale connections

        except Exception as e:
            # Log any errors during connection closure
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error closing connections: {e}")

        return response


class LogUserLastLoginConnectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.user.is_authenticated:
            return response
        logger = logging.getLogger(__name__)
        now = django_timezone.now()
        if request.user.last_login:
            if now - request.user.last_login >= timedelta(hours=1):
                request.user.last_login = now
                request.user.save()
                logger.info(f"User {request.user} logged in at {now}")
        else:
            request.user.last_login = now
            request.user.save()
            logger.info(f"User {request.user} logged in at {now}")
        return response


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        base_key = f"metrics:api:{request.path}:{today}"

        try:
            logging.info(
                "Request to '%s' processed in %.2f ms.",
                request.path,
                duration
            )
            cache.add(f"{base_key}:count", 0, TTL)
            cache.add(f"{base_key}:total_time", 0.0, TTL)
            cache.incr(f"{base_key}:count")

            total_time = (cache.get(f"{base_key}:total_time") or 0.0) + duration
            cache.set(f"{base_key}:total_time", total_time, TTL)

            # Register this base_key in the tracked set
            tracked = cache.get(ACTIVE_KEYS_KEY) or set()
            if base_key not in tracked:
                tracked.add(base_key)
                cache.set(ACTIVE_KEYS_KEY, tracked, TTL)
            logging.info(f"Request to '{request.path}' processed in {duration:.2f} ms.")
        except Exception as e:
            Logger.error(LogSchema(
                sender="RequestTimingMiddleware",
                title="Failed to log request timing",
                description=str(e)
            ).__dict__, exc_info=True)
        return response