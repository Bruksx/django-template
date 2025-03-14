# WebSocket Endpoints

The following WebSocket endpoints are available for real-time communication:

- **Notifications:** `notification/ws/notifications/?token={user.token}`
- **Chat Conversations:** `ws/chats/<uuid:conversation_uid>/?token={user.token}`

## Chat WebSocket Schema
The `ChatWebsocketSchema` defines the structure of WebSocket messages for chat-related events.

### Schema Definition
```python
@dataclass
class ChatWebsocketSchema:
    sender_id: str
    sender: str
    chat_id: str
    action: Literal["new_message", "is_typing", "stopped_typing", "read_message"]
    data: Optional[Any] = None  # Contains chat-related data
    data_type: Optional[Literal["chat", "message"]] = None
```

### `data` Field Example
The `data` field in `ChatWebsocketSchema` can contain detailed information about a chat message. Below is a sample structure:

```json
{
  "sender": {
    "photo_url": "string",
    "uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "type": "string"
  },
  "conversation_uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "job_post": {
    "country": "string",
    "job_title": "string",
    "job_business": "string",
    "job_business_logo": "string",
    "uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "created_at": "2025-03-14T14:56:24.637Z"
  },
  "read": true,
  "attachments": [
    {
      "file_url": "string",
      "uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "file_type": "string",
      "created_at": "2025-03-14T14:56:24.637Z"
    }
  ],
  "uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "body": "string",
  "created_at": "2025-03-14T14:56:24.637Z"
}
```

---

## Notification WebSocket Schema
The `NotificationWebsocketSchema` defines the structure of WebSocket messages for notification-related events.

### Schema Definition
```python
@dataclass
class NotificationWebsocketSchema:
    title: str
    description: str
    action: Optional[Literal["new", "update", "delete"]] = None
    entity_uid: Optional[str] = None  # UUID string
    entity_str: Optional[str] = None
    notification_type: Optional[Literal["applicants", "matching", "sharing", "performance", "user", "assignment"]] = None
    entity: Optional[Literal["job", "chat", "talent", "business", "job application", "job post", "customer case", "job application withdrawal", "settings", "user"]] = None
```

This schema allows real-time notifications to be sent when specific events occur, such as job postings, chat updates, or user-related activities.

---

This documentation provides a structured overview of the WebSocket schemas and expected data formats. Let me know if you need further refinements!

