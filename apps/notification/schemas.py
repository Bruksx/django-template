from typing import Optional, List
from uuid import UUID

from ninja import ModelSchema
from ninja import Schema, Field
from ninja_extra.schemas import PaginatedResponseSchema
from notification.enums import EntityActionType, EntityType, NotificationType
from notification.models import Notification, BusinessUserNotificationSettings


class NotificationSchema(ModelSchema):
    action: Optional[EntityActionType] = None
    entity: Optional[EntityType] = None
    notification_type: Optional[NotificationType] = None
    is_read : Optional[bool] = False

    class Meta:
        model = Notification
        fields = ("uid", "title", "description", "action",
                  "entity", "entity_uid", "entity_str",
                  "notification_type")

    @staticmethod
    def resolve_is_read(obj, context):
        request = context.get("request")
        user = request.user
        return obj.is_read(user)

class NotificationSettingsSchema(ModelSchema):
    class Meta:
        model = BusinessUserNotificationSettings
        fields = ("applicants_notification", "matching_notification",
                  "sharing_notification", "performance_notification",
                  "user_notification", "assignment_notification")

class NotificationFilterSchema(Schema):
    page: Optional[int] = 1
    page_size: Optional[int] = 10
    viewed: Optional[bool] = Field(None, description="Viewed notifications")
    excludes: Optional[str] = Field(None,
                                    description=f"Comma separated list of entity types: {', '.join(EntityType.values())}",
                                    )

class PaginatedNotificationSchema(PaginatedResponseSchema[NotificationSchema]):
    unread_count: int

class BulkActionNotificationSchema(Schema):
    uids: Optional[List[UUID]]
    all: bool = False
    excludes: Optional[str] = Field(None,
                                    description=f"Comma separated list of entity types: {', '.join(EntityType.values())}",
                                    )