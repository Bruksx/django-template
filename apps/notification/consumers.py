import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from notification.models import BusinessUserNotificationSettings


class NotificationConsumer(AsyncWebsocketConsumer):
        def __init__(self, *args, **kwargs):
            super().__init__(args, kwargs)
            self.user = None

        async def connect(self):
            user = self.scope.get("user")
            if not user:
                await self.close()
                return
            self.user = user
            self.groups = await sync_to_async(user.user_notification_groups)()
            for group in self.groups:
                await self.channel_layer.group_add(group, self.channel_name)
            await self.accept()
            await self.send(f"{self.user} just connected to notifier")

        async def websocket_receive(self, data):
            data = json.loads(data["text"])
            channel = data.get("channel")
            if channel in self.groups:
                await self.channel_layer.group_send(
                    channel, {"type": "notify", "data": json.dumps(data)}
                )

        async def notify(self, event):
            data = json.loads(event["data"])
            notification_type = data.get("notification_type", None)
            channel = data.pop("channel")
            should_send = await sync_to_async(BusinessUserNotificationSettings.should_send_notification)(self.user, notification_type)
            if channel and channel in self.groups and should_send:
                event["data"] = json.dumps(data)
                await self.send(text_data=event["data"])

        async def disconnect(self, code):
            if self.user:
                for group in self.groups:
                    await self.channel_layer.group_discard(group, self.channel_name)
                self.user = None
            await super().disconnect(code)
