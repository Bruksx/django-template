from dataclasses import dataclass
from typing import Literal, Optional, Any

"""
SOCKET URLS

notification/ws/notifications/?token={user.token}
ws/chats/<uuid:conversation_uid>/?token={user.token}


"""

@dataclass
class ChatWebsocketSchema:
    sender_id: str
    sender: str
    chat_id: str
    action: Literal["new_message", "is_typing", "stopped_typing", "read_message"]
    data: Optional[Any] = None
    data_type: Optional[Literal["chat", "message"]] = None




@dataclass
class NotificationWebsocketSchema:
    title: str
    description: str
    action: Optional[Literal["new", "update", "delete"]]=None
    entity_uid: Optional[str] = None # UUID string
    entity_str: Optional[str] = None
    notification_type: Optional[Literal["applicants", "matching", "sharing", "performance", "user", "assignment"]] = None
    entity: Optional[Literal["job", "chat", "talent", "business", "job application", "job post", "customer case", "job application withdrawal", "settings", "user"]] = None

