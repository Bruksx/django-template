import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .schemas import ChatWebsocketSchema
from ..decorators import test_env_decorator


@test_env_decorator()
def send_ws(channel:str, data: ChatWebsocketSchema):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        channel,
        {"type": "notify", "data": json.dumps(data)}
    )
    # async_to_sync(channel_layer.send)(channel, data)
