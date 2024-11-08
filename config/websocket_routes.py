from django.urls import path

from apps.chats.consumers import ChatConsumer
from apps.notification.consumers import NotificationConsumer

urlpatterns = [
    path("ws/chats/<uuid:conversation_uid>/", ChatConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),

]