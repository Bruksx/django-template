import logging
from typing import List

from accounts.models import User
from core.models import BaseModel
from django.db import models
from django.db.models import Q
from jobs.models import JobPost

from helpers.websocket.schemas import ChatWebsocketSchema
from helpers.websocket.utils import send_ws
from .enums import ChatMessageAttachmentType


# Create your models here.
class Conversation(BaseModel):
    users = models.ManyToManyField(User)
    last_message_time = models.DateTimeField(default=None, null=True)

    def save(self, *args, **kwargs):
        """if self.pk is None:
            existing_conversations = Conversation.objects.filter(
                users__in=self.users.all()
            ).annotate(num_users=models.Count('users')).filter(num_users=self.users.count())

            if existing_conversations.exists():
                raise ValueError("A conversation between these users already exists.")"""
        super().save(*args, **kwargs)

    def last_message(self):
        return self.message_set.last()

    def read_messages(self, message_ids:List[int], user_id:int):
        from .schemas import ChatMessageListSchema
        user = User.objects.filter(id=user_id).first()
        if not user:
            return
        read_message_ids = user.readmessagelog_set.filter(message_id__in=message_ids).only("message_id").values_list("message_id", flat=True)
        ids = [msg_id for msg_id in message_ids if msg_id not in read_message_ids]
        messages = Message.objects.filter(~Q(sender=user) & Q(id__in=ids))
        logs = list()
        for message in messages:
            logs.append(ReadMessageLog(reader=user, message=message))
            send_ws(channel=str(self.uid), data=ChatWebsocketSchema(
                sender_id=str(user.uid),
                chat_id = str(self.uid),
                sender=user.get_full_name(),
                action="read_message",
                data=ChatMessageListSchema.from_orm(message).model_json_schema(),
                data_type="message")
             )
        ReadMessageLog.objects.bulk_create(logs)
        return

    def unread_messages_count(self, user):
        read_message_ids = user.readmessagelog_set.values_list("message_id", flat=True)
        return self.message_set.exclude(Q(id__in=read_message_ids)|Q(sender=user)).count()


class Message(BaseModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True)
    sender = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    job_post = models.ForeignKey(JobPost, on_delete=models.SET_NULL, null=True, default=None)
    body = models.TextField()

    def __str__(self) -> str:
        return f"{self.sender}"

    def notify_chat(self):
        from .schemas import ChatMessageListSchema
        send_ws(channel=str(self.conversation.uid), data=ChatWebsocketSchema(
            sender_id=str(self.sender.uid),
            sender=self.sender.get_full_name(),
            chat_id = str(self.conversation.uid),
            action="new_message",
            data=ChatMessageListSchema.from_orm(self).model_json_schema(),
            data_type="message")
        )


class ReadMessageLog(BaseModel):
    reader = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    message = models.ForeignKey(Message, on_delete=models.DO_NOTHING)


class MessageAttachment(BaseModel):
    message = models.ForeignKey("Message", on_delete=models.CASCADE)
    file_type = models.CharField(choices=ChatMessageAttachmentType.choices())
    file = models.FileField(upload_to="chat_attachments")

    def file_url(self):
        if self.file:
            return  self.file.url
        return None