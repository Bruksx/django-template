import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .schemas import ChatWebsocketSchema, NotificationWebsocketSchema
from ..decorators import test_env_decorator
from ..loggers import Logger


@test_env_decorator()
def send_ws(channel:str, data: ChatWebsocketSchema|NotificationWebsocketSchema):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            channel,
            {"type": "notify", "data": json.dumps(data.__dict__)}
        )
    except Exception as e:
        Logger.error(dict(
            sender="Websocket Service",
            title="An Error Occurred",
            description=str(e)
        ))
