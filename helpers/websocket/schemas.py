from dataclasses import dataclass
from typing import Literal, Optional, Any


@dataclass
class ChatWebsocketSchema:
    sender_id: str
    sender: str
    chat_id: str
    action: Literal["new_message", "is_typing", "stopped_typing", "new_user", "read_message"]
    data: Optional[Any] = None
    data_type: Optional[Literal["chat", "message"]] = None

@dataclass
class NotificationWebsocketSchema:
    ...
