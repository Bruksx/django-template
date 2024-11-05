import json

from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
        def __init__(self, *args, **kwargs):
            super().__init__(args, kwargs)
            self.user = None

        async def connect(self):
            user = self.scope.get("user")
            if not user:
                await self.close()
                return
            await self.channel_layer.group_add(str(self.user.uid), self.channel_name)
            await self.accept()
            await self.send(f"{self.user} just connected to notifier")

        async def websocket_receive(self, payload):
            payload = json.loads(payload["text"])
            data = payload.get("data")
            await self.channel_layer.group_send(
                str(self.user.uid), {"type": "notify", "data": json.dumps(data)}
            )

        async def notify(self, event):
            await self.send(text_data=event["data"])

        async def disconnect(self, code):
            await self.channel_layer.group_discard(str(self.user.uid), self.channel_name)
            self.user = None
            await super().disconnect(code)
