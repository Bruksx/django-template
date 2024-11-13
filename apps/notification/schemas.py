from ninja import ModelSchema

from notification.models import Notification, BusinessUserNotificationSettings


class NotificationSchema(ModelSchema):
    class Meta:
        model = Notification
        fields = ("title", "description", "action",
                  "entity", "entity_uid", "entity_str",
                  "notification_type")

class NotificationSettingsSchema(ModelSchema):
    class Meta:
        model = BusinessUserNotificationSettings
        fields = ("applicants_notification", "matching_notification",
                  "sharing_notification", "performance_notification",
                  "user_notification", "assignment_notification")
