import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from chats.models import Conversation


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





