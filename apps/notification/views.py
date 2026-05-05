from uuid import UUID

from config.permissions import IsBusinessUser
from django.db import transaction
from monkeypatches.q_cluster import async_task
from monkeypatches.response import Response
from ninja import Router, PatchDict, Query
from ninja_jwt.authentication import JWTAuth

from jobs.business_views import pagination_class
from notification.models import BusinessUserNotificationSettings, Notification
from notification.schemas import NotificationFilterSchema, PaginatedNotificationSchema, BulkActionNotificationSchema
from notification.schemas import NotificationSettingsSchema, NotificationSchema
from notification.service import bulk_read_notifications_service, bulk_delete_notifications_service

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


@router.get("", auth=JWTAuth(), response=PaginatedNotificationSchema)
def get_notifications(request, filters: NotificationFilterSchema = Query(...)):
    if hasattr(request.user, "businessuser"):
        queryset = request.user.businessuser.notifications(viewed=filters.viewed, excludes=filters.excludes)
        unread_count = (Notification.can_view_annotation(request.user.businessuser.notifications(viewed=False, excludes=filters.excludes), request.user).
                    count())
    elif hasattr(request.user, "talent"):
        queryset =  request.user.talent.notifications(viewed=filters.viewed, excludes=filters.excludes)
        unread_count = (Notification.can_view_annotation(request.user.talent.notifications(viewed=False, excludes=filters.excludes), request.user)
                        .count())
    else:
        queryset = Notification.objects.none()
        unread_count = 0
    queryset = Notification.can_view_annotation(queryset, request.user)
    pagination = pagination_class(filters.page_size).Input(page=filters.page, page_size=filters.page_size)
    return pagination_class(filters.page_size).paginate_queryset(
        queryset=queryset,
        request=request,
        pagination=pagination,
        unread_count=unread_count
    )

@router.patch("{notification_uid}/read", auth=JWTAuth())
def read_notification(request, notification_uid: UUID):
    notification = Notification.objects.filter(uid=notification_uid).first()
    if not notification:
        return Response(status=404, data={"message": "Notification not found"})
    notification.view(request.user)
    return Response(status=200, data={"message": "Notification marked as read"})


@router.patch("", auth=JWTAuth())
def bulk_read_notifications(request, data: BulkActionNotificationSchema):
    if not data.uids and data.all is False:
        return Response(status=400, data={"message": "You have not selected any notifications"})

    if hasattr(request.user, "businessuser"):
        notifications = request.user.businessuser.notifications(viewed=False, excludes=data.excludes)
    elif hasattr(request.user, "talent"):
        notifications = request.user.talent.notifications(viewed=False, excludes=data.excludes)
    else:
        notifications = Notification.objects.none()

    if data.uids:
        notifications = notifications.filter(uid__in=data.uids)

    async_task(bulk_read_notifications_service, notifications, request.user)

    return Response(status=200, data={"message": "Notifications marked read successfully"})


@router.delete("", auth=JWTAuth())
def delete_notifications(request, data: BulkActionNotificationSchema):
    if not data.uids and data.all is False:
        return Response(status=400, data={"message": "You have not selected any notifications"})

    if hasattr(request.user, "businessuser"):
        notifications = request.user.businessuser.notifications(excludes=data.excludes)
    elif hasattr(request.user, "talent"):
        notifications = request.user.talent.notifications(excludes=data.excludes)
    else:
        notifications = Notification.objects.none()

    if data.uids:
        notifications = notifications.filter(uid__in=data.uids)

    async_task(bulk_delete_notifications_service, notifications, request.user)

    return Response(status=204, data={"message": "Notifications deleted successfully"})


@ws_router.get('ws/notifications/', response={200: NotificationSchema},
             tags=["Websocket"])
def websocket_notification(request, token: str):
    return Response(status=200, data={"message": "Message sent successfully"})