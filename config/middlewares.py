import logging
import time
from urllib.parse import parse_qsl

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.utils import timezone
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


class RequestTimingMiddleware:
    """
    A Django middleware designed to calculate the elapsed time
    required to process each incoming HTTP request. This helps in
    identifying performance bottlenecks and optimizing your application.
    """

    def __init__(self, get_response):
        """
        The constructor, receiving the next callable in the middleware chain.
        """
        self.get_response = get_response
        # Additional initialization logic could be added here if needed.

    def __call__(self, request):
        """
        This method is invoked for every request and wraps the response
        generation with our timing mechanism.

        Args:
            request: The HTTP request object.

        Returns:
            The HTTP response object.
        """
        # Record the start time of the request processing.
        start_time = time.time()

        # Allow the request to proceed to the view, or the next middleware,
        # and wait for the response.
        response = self.get_response(request)

        # Record the end time of the request processing.
        end_time = time.time()

        # Calculate the duration in milliseconds.
        duration = (end_time - start_time) * 1000

        # Log the request path and the duration.
        logging.info(
            "Request to '%s' processed in %.2f ms.",
            request.path,
            duration
        )

        # Return the response to continue the request-response cycle.
        return response


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
        # Process the request (view execution, including any transaction.atomic)
        response = self.get_response(request)

        # Log the last login time of the user
        if not request.user.is_authenticated:
            return response
        logger = logging.getLogger(__name__)
        last_login = cache.get(f"last_login_{request.user.id}")
        if not last_login:
            last_login = request.user.last_login

        if last_login.date == timezone.now().date():
            return response
        request.user.last_login = timezone.now()
        request.user.save()
        last_login = request.user.last_login
        cache.set(
            key=f"last_login_{request.user.id}",
            value=last_login,
            timeout=3600
        )
        logger.info(f"User {request.user} logged in at {last_login}")
        return response
