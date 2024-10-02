"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.routing import URLRouter, ProtocolTypeRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from config.middlewares import QueryAuthMiddleware
from config.websocket_routes import urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

http_application = get_asgi_application()
websocket_application = AllowedHostsOriginValidator(
        QueryAuthMiddleware(
            URLRouter(
                urlpatterns
            )
        )
)


application = ProtocolTypeRouter({
    "http": http_application,
    "websocket": websocket_application
})


