from uuid import UUID

from config.permissions import IsBusinessUser
from django.db import transaction
from monkeypatches.response import Response
from ninja import Router, PatchDict
from ninja_extra import paginate
from ninja_jwt.authentication import JWTAuth
from config.websocket_routes import ws_router
from notification.models import BusinessUserNotificationSettings, Notification
from notification.schemas import NotificationSettingsSchema, NotificationSchema
from paginations import CustomPageNumberPaginationExtra as PageNumberPaginationExtra
from paginations import CustomPaginatedResponseSchema as PaginatedResponseSchema

# Create your views here.
router = Router(tags=["Notifications"])


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
def get_notifications(request, viewed: bool = False):
    if hasattr(request.user, "businessuser"):
        return request.user.businessuser.notifications(viewed=viewed)
    elif hasattr(request.user, "talent"):
        return request.user.talent.notifications(viewed=viewed)
    return Notification.objects.none()

@router.patch("{notification_uid}/read", auth=JWTAuth())
def read_notification(request, notification_uid: UUID):
    notification = Notification.objects.filter(uid=notification_uid).first()
    if not notification:
        return Response(status=404, data={"message": "Notification not found"})
    notification.view(request.user)
    return Response(status=200, data={"message": "Notification marked as read"})


@ws_router.get('notifications', response={200: NotificationSchema},
             tags=["Websocket"])
def websocket_notification(request, token: str):
    return Response(status=200, data={"message": "Message sent successfully"})