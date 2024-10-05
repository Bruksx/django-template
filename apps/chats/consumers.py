import json
import logging

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.exceptions import InvalidChannelLayerError, AcceptConnection, DenyConnection
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from chats.models import Conversation

class SyncChatsConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.chat_ids = None
        self.user = None

    def websocket_connect(self, message):
        """
        Called when a WebSocket connection is opened.
        """
        try:
            for group in self.groups:
                async_to_sync(self.channel_layer.group_add)(group, self.channel_name)
        except AttributeError:
            raise InvalidChannelLayerError(
                "BACKEND is unconfigured or doesn't support groups"
            )
        try:
            self.connect()
        except AcceptConnection:
            self.accept()
        except DenyConnection:
            self.close()

    def get_chat_uuids(self):
        return Conversation.objects.filter(users__id=self.user.id).values_list("uid", flat=True)\


    def connect(self):
        user = self.scope.get("user")
        if not user:
            self.close()
            return
        self.user = user
        self.chat_ids = self.get_chat_uuids()
        for chat_id in self.chat_ids:
            async_to_sync(self.channel_layer.group_add)(str(chat_id), self.channel_name)
        self.accept()
        self.send(f"{self.user} just connected to connections")


    def websocket_receive(self, payload):
        payload = json.loads(payload["text"])
        data = payload.get("data")
        chat_uuid = data.get("chat_id")
        if not chat_uuid or chat_uuid not in self.chat_ids:
            return
        async_to_sync(self.channel_layer.group_send)(
            str(chat_uuid), {"type": "notify", "data": json.dumps(data)}
        )

    def notify(self, event):
        self.send(text_data=event["data"])

    def disconnect(self, code):
        chat_ids = self.chat_ids or list()
        for chat_id in chat_ids:
            async_to_sync(self.channel_layer.group_discard)(str(chat_id), self.channel_name)
        self.chat_ids = None
        self.user = None
        super().disconnect(code)

class ChatsConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.chat_ids = None
        self.user = None

    async def websocket_connect(self, message):
        """
        Called when a WebSocket connection is opened.
        """
        try:
            for group in self.groups:
                await self.channel_layer.group_add(group, self.channel_name)
        except AttributeError:
            raise InvalidChannelLayerError(
                "BACKEND is unconfigured or doesn't support groups"
            )
        try:
            await self.connect()
        except AcceptConnection:
            await self.accept()
        except DenyConnection:
            await self.close()

    @database_sync_to_async
    def get_chat_uuids(self):
        return Conversation.objects.filter(users__id=self.user.id).values_list("uid", flat=True)\


    async def connect(self):
        user = self.scope.get("user")
        if not user:
            await self.close()
            return
        self.user = user
        self.chat_ids = await self.get_chat_uuids()
        async for chat_id in self.chat_ids:
            await self.channel_layer.group_add(str(chat_id), self.channel_name)
        await self.accept()
        await self.send(f"{self.user} just connected to connections")


    async def websocket_receive(self, payload):
        payload = json.loads(payload["text"])
        data = payload.get("data")
        chat_uuid = data.get("chat_id")
        if not chat_uuid or chat_uuid not in self.chat_ids:
            return
        await self.channel_layer.group_send(
            str(chat_uuid), {"type": "notify", "data": json.dumps(data)}
        )

    async def notify(self, event):
        await self.send(text_data=event["data"])

    async def disconnect(self, code):
        chat_ids = self.chat_ids or list()
        for chat_id in chat_ids:
            await self.channel_layer.group_discard(str(chat_id), self.channel_name)
        self.chat_ids = None
        self.user = None
        await super().disconnect(code)

class ChatConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.chat = None
        self.user = None

    @database_sync_to_async
    def get_conversation(self):
        conversation_uid = self.scope["url_route"]["kwargs"].get("conversation_uid")
        if not conversation_uid:
            return
        return Conversation.objects.filter(uid=conversation_uid, users__id=self.user.id).first()


    async def connect(self):
        user = self.scope.get("user")
        if not user:
            await self.close()
            return
        self.user = user
        chat = await self.get_conversation()
        if not chat:
            await self.close()
            return
        self.chat = chat
        await self.channel_layer.group_add(str(self.chat.uid), self.channel_name)
        await self.accept()


    async def websocket_receive(self, data):
        data = json.loads(data["text"])
        await self.channel_layer.group_send(
            str(self.chat.uid), {"type": "notify", "data": json.dumps(data)}
        )

    async def disconnect(self, code):
        if self.chat:
            await self.channel_layer.group_discard(str(self.chat.uid), self.channel_name)
        self.chat = None
        self.user = None
        await super().disconnect(code)

    async def notify(self, event):
        await self.send(text_data=event["data"])






