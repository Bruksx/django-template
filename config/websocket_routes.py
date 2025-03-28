from django.urls import path
from ninja import Router

from apps.chats.consumers import ChatConsumer
from apps.notification.consumers import NotificationConsumer

ws_router = Router(tags=["Websocket"])

urlpatterns = [
    path("ws/chats/<uuid:conversation_uid>/", ChatConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),

]