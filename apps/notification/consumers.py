import json

from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
        def __init__(self, *args, **kwargs):
            super().__init__(args, kwargs)
            self.group_name = None
            self.user = None

        async def connect(self):
            user = self.scope.get("user")
            if not user:
                await self.close()
                return
            self.user = user
            self.group_name = user.notification_group_name
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            await self.send(f"{self.user} just connected to notifier")

        async def websocket_receive(self, payload):
            payload = json.loads(payload["text"])
            data = payload.get("data")
            await self.channel_layer.group_send(
                self.group_name, {"type": "notify", "data": json.dumps(data)}
            )

        async def notify(self, event):
            await self.send(text_data=event["data"])

        async def disconnect(self, code):
            if self.user:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                self.user = None
            await super().disconnect(code)
