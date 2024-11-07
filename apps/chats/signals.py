

from chats.models import Message
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    if created:
        instance.conversation.last_message_time = instance.created_at
        instance.conversation.save()
        instance.notify_chat()

#todo: notification to signal new chat