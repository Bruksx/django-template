from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from notification.models import Notification


def delete_notifications_older_than_a_month():
    with transaction.atomic():
        Notification.objects.filter(created_at__lt=timezone.now() - timedelta(days=30)).delete()
    return