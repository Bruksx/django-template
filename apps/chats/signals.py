

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from chats.models import Message


@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    if created:
        instance.conversation.last_message_time = instance.created_at
        instance.conversation.save()