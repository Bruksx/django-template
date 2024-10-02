import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .schemas import ChatWebsocketSchema

def send_ws(channel:str, data: ChatWebsocketSchema):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        channel,
        {"type": "notify", "data": json.dumps(data.dict())}
    )
