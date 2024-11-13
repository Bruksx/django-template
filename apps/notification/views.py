from django.db import transaction
from ninja import Router, PatchDict
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth

from notification.models import BusinessUserNotificationSettings
from notification.schemas import NotificationSettingsSchema
from config.permissions import IsBusinessUser

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
