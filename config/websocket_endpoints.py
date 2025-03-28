from ninja import NinjaAPI

from apps.core.renderers import ORJSONRenderer
from .websocket_routes import ws_router
websocket = NinjaAPI(docs_url="docs",  renderer=ORJSONRenderer(),
                     urls_namespace="websocket")
websocket.add_router("", ws_router)
