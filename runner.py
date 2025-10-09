import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from notification.models import Notification

notifications = Notification.objects.iterator()
for notification in notifications:
    print("previous recipients: ", notification.all_recipients.count())
    notification.all_recipients.set(notification.get_recipients())
    notification.save()
    print("current recipients: ", notification.all_recipients.count(), "\n")