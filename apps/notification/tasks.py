from datetime import timedelta

from django.utils import timezone

from notification.models import Notification


def delete_notifications_older_than_a_month():
    Notification.objects.filter(created_at__lt=timezone.now() - timedelta(days=30)).delete()
    return