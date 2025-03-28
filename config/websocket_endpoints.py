from ninja import NinjaAPI

from apps.core.renderers import ORJSONRenderer

websocket = NinjaAPI(docs_url="websocket-docs",  renderer=ORJSONRenderer(),
                     urls_namespace="websocket")
websocket.add_router("", "chats.views.ws_router")
websocket.add_router("", "notification.views.ws_router")
