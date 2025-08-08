from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from notification.models import Notification


@receiver(post_save, sender=Notification)
def update_recipients(sender, instance, created, **kwargs):
    if created:
        instance.all_recipients.add(*instance.get_recipients())
        instance.save()