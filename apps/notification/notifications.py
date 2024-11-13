from .enums import EntityActionType
from .enums import EntityType, NotificationType
from .models import Notification


def send_new_chat_notification(chat):
    notification = Notification.objects.create(
        title="New Chat Notification",
        description="You have a new chat",
        action=EntityActionType.NEW,
        notification_type=NotificationType.USER.value,
        entity=EntityType.CHAT,
        entity_uid=chat.uid,
        entity_str=str(chat),
    )
    notification.recipient_users.add(*chat.users.all())
    notification.save()
    notification.notify()



