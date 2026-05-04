from typing import Optional

from django.db import models
from django.db.models import Q, Case, When, Value, F
from helpers.websocket.utils import send_ws

from accounts.enums import BusinessUserRoleType, UserType
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
    all_recipients = models.ManyToManyField("accounts.User", blank=True, related_name="all_recipients")
    business = models.ForeignKey("accounts.Business", on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=150, choices=BusinessUserRoleType.choices, null=True)

    def notify(self):
        notification = dict(
            title=self.title,
            description=self.description,
            action=self.action,
            entity=self.entity,
            entity_uid=str(self.entity_uid),
            entity_str=self.entity_str,
            notification_type=self.notification_type
        )
        # sends to selected users
        if self.all_recipients.count() > 0:
            for user in self.all_recipients.iterator():
                send_ws(user.notification_group_name, notification)
        return


    def is_read(self, user):
        return self.viewers.filter(id=user.id).exists()


    def get_recipients(self):
        from accounts.models import User
        group_query = Q()
        queryset = self.recipient_users.all()
        if len(self.recipient_groups) > 0:
            for group in self.recipient_groups:
                if group == NotificationGroup.BUSINESS_USERS.value:
                    business_user_query = Q(type=UserType.BUSINESS.value)
                    if self.role:
                        business_user_query = business_user_query & Q(businessuser__role=self.role)
                    if self.business:
                        business_user_query = business_user_query & Q(businessuser__business=self.business)
                    group_query = group_query | business_user_query

                elif group == NotificationGroup.TALENTS.value:
                    group_query = group_query | Q(type=UserType.TALENT.value)
        if group_query:
            return User.objects.filter(group_query).union(queryset)
        return queryset

    def view(self, user):
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
                return ((self.role and self.role == user.business_user.role) or
                (NotificationGroup.BUSINESS_USERS.value in self.recipient_groups))
        return False

    @staticmethod
    def can_view_annotation(queryset, user):
        allowed = Case(When(Q(Q(recipient_users__id=user.id) | Q(
                recipient_groups__contains=[NotificationGroup.ALL_USERS.value])),
                            then=Value(True)),
                       default=Value(False))
        queryset = queryset.annotate(allowed=allowed)
        can_view = Q(allowed=True)
        if hasattr(user, 'talent'):
            can_view = can_view | Q(recipient_groups__contains=[NotificationGroup.TALENTS.value])

        elif hasattr(user, "businessuser"):
            business_user = user.businessuser

            same_role=Case(When(
                Q(business=business_user.business, role=business_user.role),
                then=Value(True)
            ), default=Value(False))

            same_group=Case(When(
                Q(business=business_user.business, recipient_groups__contains=[NotificationGroup.BUSINESS_USERS.value]),
                then=Value(True)
            ), default=Value(False))

            queryset = queryset.annotate(same_role=same_role, same_group=same_group,
                has_setting=Case(When(notification_type__isnull=False,
                                 then=Value(hasattr(business_user, "businessusernotificationsettings") and business_user.businessusernotificationsettings.should_notify(F('notification_type')))),
                            default=Value(True))
            )
            can_view = can_view | Q(Q(has_setting=True) & Q(Q(same_role=True) | Q(same_group=True)))
        return queryset.filter(can_view)





    def delete_notification(self, user):
        if self.all_recipients.filter(id=user.id).exists():
            self.all_recipients.remove(user)
        self.all_recipients.remove(user)
        if self.viewers.filter(id=user.id).exists():
            self.viewers.remove(user)
        if self.recipient_users.filter(id=user.id).exists():
            self.recipient_users.remove(user)
        self.save()




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

    def notifications(self, viewed:Optional[bool]=None, excludes: Optional[str]=None):
       initial_query = Q(Q(
            Q(notification_type__in=self.allowed_notification_types()) |
            Q(notification_type__isnull=True)
        ) & Q(all_recipients__id=self.business_user.user.id))


       notifications = Notification.objects.filter(initial_query)
       if viewed is True:
            notifications = notifications.filter(
                viewers__id=self.business_user.user.id
            )
       elif viewed is False:
            notifications = notifications.exclude(
                viewers__id=self.business_user.user.id
            )

       if excludes:
            excludes = excludes.split(",")
            notifications = notifications.exclude(entity__in=excludes)
       return notifications.order_by("-id")

    @classmethod
    def should_send_notification(cls, user, notification_type:Optional[str]):
        if not user:
            return False
        notification_settings = cls.objects.filter(business_user__user_id=user.id).first()
        if not notification_settings:
            return True
        return notification_settings.should_notify(notification_type)

