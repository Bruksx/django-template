from dataclasses import dataclass
from typing import Literal, Optional, Any

"""
SOCKET URLS

ws/notifications/?token={user.token}
ws/chats/<uuid:conversation_uid>/?token={user.token}


"""

@dataclass
class ChatWebsocketSchema:
    sender_id: Optional[str]
    sender: Optional[str]
    recipient: Optional[Any]
    chat_id: Optional[str]
    action: Literal["new_message", "is_typing", "stopped_typing", "read_message"]
    data: Optional[Any] = None



@dataclass
class NotificationWebsocketSchema:
    title: str
    description: Optional[str] = None
    action: Optional[Literal["new", "update", "delete"]]=None
    entity_uid: Optional[str] = None # UUID string
    entity_str: Optional[str] = None
    notification_type: Optional[Literal["applicants", "matching", "sharing", "performance", "user", "assignment"]] = None
    entity: Optional[Literal["job", "chat", "talent", "business", "job application", "job post", "customer case", "job application withdrawal", "settings", "user"]] = None

