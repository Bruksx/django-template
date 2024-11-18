import json
from typing import List

from django.db import models
from django.db.models import Q
from helpers.websocket.utils import send_ws

from accounts.models import User
from core.models import BaseModel
from jobs.models import JobPost
from .enums import ChatMessageAttachmentType


# Create your models here.
class Conversation(BaseModel):
    users = models.ManyToManyField(User)
    locked = models.BooleanField(default=False)
    last_message_time = models.DateTimeField(null=True)

    @property
    def chat_group_name(self):
        return f"chat_{self.uid}"

    def get_recipient(self, user):
        recipient = self.users.exclude(id=user.id).first()
        if not recipient:
            return None
        return recipient

    def last_message(self):
        return self.message_set.last()

    def __str__(self):
        return f"{self.users.first()} - {self.users.last()}"

    #TODO When a conversation is created, a notification should sent to the concerned users

    def save(self, *args, **kwargs):
        """if self.pk is None:
            existing_conversations = Conversation.objects.filter(
                users__in=self.users.all()
            ).annotate(num_users=models.Count('users')).filter(num_users=self.users.count())

            if existing_conversations.exists():
                raise ValueError("A conversation between these users already exists.")"""
        super().save(*args, **kwargs)

    def unread_messages(self, user_id:int):
        return self.message_set.exclude(sender_id=user_id).exclude(readers__id=user_id)

    def read_messages(self, message_ids:List[int], user_id:int):
        from .schemas import ChatMessageListSchema
        user = User.objects.filter(id=user_id).first()
        if not user:
            return
        messages = self.unread_messages(user_id=user_id).filter(id__in=message_ids)
        for message in messages:
            message.readers.add(user)
            message.save()
            send_ws(channel=self.chat_group_name, data=dict(
                sender_id=str(user.uid),
                chat_id = str(self.uid),
                sender=user.get_full_name(),
                action="read_message",
                data=json.loads(ChatMessageListSchema.from_orm(message).model_dump_json()),
                data_type="message")
             )
        return

    def unread_messages_count(self, user):
        return self.unread_messages(user_id=user.id).count()


class Message(BaseModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="sender", null=True)
    job_post = models.ForeignKey(JobPost, on_delete=models.SET_NULL, null=True, default=None)
    body = models.TextField()
    readers = models.ManyToManyField(User, blank=True, related_name="readers")

    def __str__(self) -> str:
        return f"{self.sender}"

    def notify_chat(self):
        from .schemas import ChatMessageListSchema
        send_ws(channel=self.conversation.chat_group_name, data=dict(
            sender_id=str(self.sender.uid),
            sender=self.sender.fullname,
            chat_id = str(self.conversation.uid),
            action="new_message",
            data=json.loads(ChatMessageListSchema.from_orm(self).model_dump_json()),
            data_type="message")
        )

class MessageAttachment(BaseModel):
    message = models.ForeignKey("Message", on_delete=models.CASCADE)
    file_type = models.CharField(choices=ChatMessageAttachmentType.choices())
    file = models.FileField(upload_to="chat_attachments")

    def file_url(self):
        if self.file:
            return  self.file.url
        return None