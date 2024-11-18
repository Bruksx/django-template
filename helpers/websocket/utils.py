import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .schemas import ChatWebsocketSchema, NotificationWebsocketSchema
from ..decorators import test_env_decorator
from ..loggers import Logger



def validate_data(data:dict):
    valid = False
    try:
        ChatWebsocketSchema(**data)
        return True
    except Exception:
        pass
    if not valid:
        try:
            NotificationWebsocketSchema(**data)
            return True
        except Exception:
            pass
    return False

@test_env_decorator()
def send_ws(channel:str, data:dict):
    is_valid = validate_data(data)
    if not is_valid:
        Logger.error(dict(
            sender="Websocket Service",
            title="Invalid Websocket Data",
            description="Please check your data format"
        ))
        return

    try:
        data["channel"] = channel
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            channel,
            {"type": "notify", "data": json.dumps(data)}
        )
    except Exception as e:
        Logger.error(dict(
            sender="Websocket Service",
            title="An Error Occurred",
            description=str(e)
        ))
