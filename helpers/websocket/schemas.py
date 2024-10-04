from typing import Optional, Literal

from ninja import Schema
from ninja.orm.fields import AnyObject


class ChatWebsocketSchema(Schema):
    sender_id: Optional[str] = None
    sender: Optional[str] = None
    chat_id: Optional[str] = None
    action: Literal["new_message", "is_typing", "stopped_typing", "new_user", "read_message"]
    data: Optional[AnyObject] = None
    data_type: Optional[Literal["chat", "message"]] = None

