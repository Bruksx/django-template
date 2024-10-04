from django.urls import re_path, path
from apps.chats.consumers import ChatConsumer, ChatsConsumer
from apps.notification.consumers import NotificationConsumer

urlpatterns = [
    path("ws/chats/", ChatsConsumer.as_asgi()),
    path("ws/chats/<uuid:conversation_id>/", ChatConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),

]