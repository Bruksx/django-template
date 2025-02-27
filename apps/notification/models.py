import json
from typing import Optional

from django.db import models
from django.db.models import Q
from helpers.websocket.utils import send_ws

from accounts.enums import BusinessUserRoleType
from core.models import BaseModel
from notification.enums import EntityType, EntityActionType, NotificationType, NotificationGroup


# Create your models here.


class Notification(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    action = models.CharField(max_length=150, choices=EntityActionType.choices, null=True)
    entity = models.CharField(max_length=150, choices=EntityType.choices, null=True)
    entity_uid = models.UUIDField(default=None, null=True)
    entity_str = models.CharField(max_length=255, null=True)
    recipient_groups = models.JSONField(default=list)
    recipient_users = models.ManyToManyField("accounts.User", blank=True)
    notification_type = models.CharField(max_length=150, choices=NotificationType.choices, null=True)
    viewers = models.ManyToManyField("accounts.User", blank=True, related_name="viewers")
    business = models.ForeignKey("accounts.Business", on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=150, choices=BusinessUserRoleType.choices, null=True)

    def notify(self):
        from notification.schemas import NotificationSchema #noqa
        notification = json.loads(NotificationSchema.from_orm(self).model_dump_json())
        # sends to selected users
        if self.recipient_users.count() > 0:
            for user in self.recipient_users.all():
                send_ws(user.notification_group_name, notification)
        # sends to groups or specific groups in a business
        if len(self.recipient_groups) > 0:
            for group in self.recipient_groups:
                channel = f"{group}_{self.business.uid}" if self.business else group
                send_ws(channel, notification)

        # sends to specific roles in a business
        if self.role and self.business:
            send_ws(f"{self.role}_{self.business.uid}", notification)
        return

    def view(self, user):
        if not self.can_view(user):
            return
        self.viewers.add(user)
        self.save()
        return

    def can_view(self, user):
        if self.recipient_users.filter(id=user.id).exists():
            return True

        if NotificationGroup.ALL_USERS.value in self.recipient_groups:
            return True

        if hasattr(user, "talent"):
            return NotificationGroup.TALENTS.value in self.recipient_groups
        elif hasattr(user, "business_user"):
            if self.notification_type:
                settings = BusinessUserNotificationSettings.objects.filter(
                    business_user=user.business_user
                ).first()
                if settings:
                    if not settings.should_notify(self.notification_type):
                        return  False
            if self.business:
                if self.role and self.role == user.business_user.role:
                    return True
                if NotificationGroup.BUSINESS_USERS.value in self.recipient_groups:
                    return True
        return False

class BusinessUserNotificationSettings(BaseModel):
    business_user = models.OneToOneField("accounts.BusinessUser", on_delete=models.CASCADE)
    applicants_notification = models.BooleanField(default=True)
    matching_notification = models.BooleanField(default=True)
    sharing_notification = models.BooleanField(default=True)
    performance_notification = models.BooleanField(default=True)
    user_notification = models.BooleanField(default=True)
    assignment_notification = models.BooleanField(default=True)

    def should_notify(self, notification_type: Optional[str] = None):
        if notification_type is None:
            return True
        if not self.applicants_notification and  notification_type == NotificationType.APPLICANTS.value:
            return False
        if not self.matching_notification and notification_type == NotificationType.MATCHING.value:
            return False
        if not self.sharing_notification and notification_type == NotificationType.SHARING.value:
            return False
        if not self.performance_notification and notification_type == NotificationType.PERFORMANCE.value:
            return False
        if not self.user_notification and notification_type == NotificationType.USER.value:
            return False
        if not self.assignment_notification and notification_type == NotificationType.ASSIGNMENT.value:
            return False
        return True


    def allowed_notification_types(self):
        types = set()
        if self.user_notification:
            types.add(NotificationType.USER.value)
        if self.sharing_notification:
            types.add(NotificationType.SHARING.value)
        if self.matching_notification:
            types.add(NotificationType.MATCHING.value)
        if self.assignment_notification:
            types.add(NotificationType.ASSIGNMENT.value)
        if self.applicants_notification:
            types.add(NotificationType.APPLICANTS.value)
        if self.performance_notification:
            types.add(NotificationType.PERFORMANCE.value)
        return types

    def notifications(self, viewed:Optional[bool]=None):
        notifications = Notification.objects.filter(
            Q(notification_type__in=self.allowed_notification_types()) |
            Q(notification_type__isnull=True)
        )
        recipients_query = Q(recipient_users__id=self.business_user.user.id)
        role_query  = Q(
            business=self.business_user.business,
            role=self.business_user.role
        )
        group_query = Q(
            Q(business=self.business_user.business, recipient_groups__contains=[NotificationGroup.BUSINESS_USERS.value])|
            Q(recipient_groups__contains=[NotificationGroup.ALL_USERS.value])|
            Q(recipient_groups__contains=[NotificationGroup.BUSINESS_USERS.value])
        )
        notifications = notifications.filter(
            recipients_query |
            role_query |
            group_query
        )

        if viewed is True:
            notifications = notifications.filter(
                viewers__id=self.business_user.user.id
            )
        elif viewed is False:
            notifications = notifications.exclude(
                viewers__id=self.business_user.user.id
            )
        return notifications.order_by("-id")

    @classmethod
    def should_send_notification(cls, user, notification_type:Optional[str]):
        if not user:
            return False
        notification_settings = cls.objects.filter(business_user__user_id=user.id).first()
        if not notification_settings:
            return True
        return notification_settings.should_notify(notification_type)

