import json

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from chats.models import Conversation


class ChatConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.group_name = None
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
        recipient = await sync_to_async(lambda x: x.users.exclude(id=user.id).first().__str__())(chat)
        self.group_name = chat.chat_group_name
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(f"{self.user} just connected to {recipient} chat")

    async def disconnect(self, code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            self.group_name = None
        self.user = None
        await super().disconnect(code)

    async def websocket_receive(self, data):
        data = json.loads(data["text"])
        await self.channel_layer.group_send(
            self.group_name, {"type": "notify", "data": json.dumps(data)}
        )

    async def notify(self, event):
        data = json.loads(event["data"])
        if data.pop("channel", None) == self.group_name:
            event["data"] = json.dumps(data)
            await self.send(text_data=event["data"])





