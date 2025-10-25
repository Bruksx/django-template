from ninja import Schema, Field
from typing import Optional

from ninja import ModelSchema

from notification.enums import EntityActionType, EntityType, NotificationType
from notification.models import Notification, BusinessUserNotificationSettings


class NotificationSchema(ModelSchema):
    action: Optional[EntityActionType] = None
    entity: Optional[EntityType] = None
    notification_type: Optional[NotificationType] = None

    class Meta:
        model = Notification
        fields = ("uid", "title", "description", "action",
                  "entity", "entity_uid", "entity_str",
                  "notification_type")

class NotificationSettingsSchema(ModelSchema):
    class Meta:
        model = BusinessUserNotificationSettings
        fields = ("applicants_notification", "matching_notification",
                  "sharing_notification", "performance_notification",
                  "user_notification", "assignment_notification")

class NotificationFilterSchema(Schema):
    viewed: bool = Field(False, description="Viewed notifications")
    excludes: Optional[str] = Field(None,
                                    description=f"Comma separated list of entity types: {', '.join(EntityType.values())}",
                                    )
