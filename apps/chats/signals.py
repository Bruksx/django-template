

from chats.models import Message
from django.db.models.signals import post_save
from django.dispatch import receiver
from notification.notifications import send_new_chat_notification


@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    if created:
        instance.conversation.last_message_time = instance.created_at
        instance.conversation.save()
        instance.notify_chat()
        if instance.conversation.message_set.count() == 1:
            send_new_chat_notification(instance.conversation)