from typing import Optional, Literal, NotRequired

from ninja import Schema
from ninja.orm.fields import AnyObject
from pydantic_core.core_schema import TypedDictSchema


class ChatWebsocketSchema(TypedDictSchema):
    sender_id: NotRequired[str]
    sender: NotRequired[str]
    chat_id: NotRequired[str]
    action: Literal["new_message", "is_typing", "stopped_typing", "new_user", "read_message"]
    data: NotRequired[AnyObject]
    data_type: NotRequired[Literal["chat", "message"]]

class NotificationWebsocketSchema(TypedDictSchema):
    ...
