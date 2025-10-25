from typing import List, Optional
from uuid import UUID

from django.db import transaction
from ninja import Router, PatchDict, Query
from ninja_extra import paginate
from ninja_jwt.authentication import JWTAuth
from notification.models import BusinessUserNotificationSettings, Notification
from notification.schemas import NotificationSettingsSchema, NotificationSchema
from paginations import CustomPageNumberPaginationExtra as PageNumberPaginationExtra
from paginations import CustomPaginatedResponseSchema as PaginatedResponseSchema

from apps.notification.schemas import NotificationFilterSchema
from config.permissions import IsBusinessUser
from monkeypatches.response import Response

# Create your views here.
router = Router(tags=["Notifications"])
ws_router = Router(tags=["Websocket"])


@router.get("business/notification-settings", auth=JWTAuth(), response=NotificationSettingsSchema)
def get_notification_settings(request):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    settings, _ = BusinessUserNotificationSettings.objects.get_or_create(business_user=business_user)
    return settings

@router.patch("business/notification-settings", auth=JWTAuth())
@transaction.atomic
def update_notification_settings(request, data: PatchDict[NotificationSettingsSchema]):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    settings = BusinessUserNotificationSettings.objects.filter(business_user=business_user).first()
    if not settings:
        BusinessUserNotificationSettings.objects.create(**data)
    else:
        settings.update(**data)
    return Response(status=200, data={"message": "Notification settings updated successfully"})


@router.get("", auth=JWTAuth(), response=PaginatedResponseSchema[NotificationSchema])
@paginate(PageNumberPaginationExtra, page_size=50)
def get_notifications(request, filters: NotificationFilterSchema = Query(...)):
    if hasattr(request.user, "businessuser"):
        return request.user.businessuser.notifications(viewed=filters.viewed, excludes=filters.excludes)
    elif hasattr(request.user, "talent"):
        return request.user.talent.notifications(viewed=filters.viewed, excludes=filters.excludes)
    return Notification.objects.none()

@router.patch("{notification_uid}/read", auth=JWTAuth())
def read_notification(request, notification_uid: UUID):
    notification = Notification.objects.filter(uid=notification_uid).first()
    if not notification:
        return Response(status=404, data={"message": "Notification not found"})
    notification.view(request.user)
    return Response(status=200, data={"message": "Notification marked as read"})


@router.delete("", auth=JWTAuth())
def delete_notifications(request, notification_uids: Optional[List[UUID]]=None, all: bool=False):
    if all is True:
        if hasattr(request.user, "businessuser"):
            notifications = request.user.businessuser.notifications()
        elif hasattr(request.user, "talent"):
            notifications =  request.user.talent.notifications()
        else:
            notifications  = Notification.objects.none()
    else:
        if not notification_uids:
            return Response(status=400, data={"message": "notification_uids is required"})
        notifications = Notification.objects.filter(uid__in=notification_uids)

    for notification in notifications.iterator():
        notification.delete_notification(request.user)
    return Response(status=204, data={"message": "Notifications deleted successfully"})


@ws_router.get('ws/notifications/', response={200: NotificationSchema},
             tags=["Websocket"])
def websocket_notification(request, token: str):
    return Response(status=200, data={"message": "Message sent successfully"})