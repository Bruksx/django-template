from django.db import models
from django.db.models import Q

from core.models import BaseModel
from accounts.models import User
from jobs.models import Job, JobPost
from .enums import ChatMessageAttachmentType


# Create your models here.
class Conversation(BaseModel):
    users = models.ManyToManyField(User)

    def save(self, *args, **kwargs):
        """if self.pk is None:
            existing_conversations = Conversation.objects.filter(
                users__in=self.users.all()
            ).annotate(num_users=models.Count('users')).filter(num_users=self.users.count())

            if existing_conversations.exists():
                raise ValueError("A conversation between these users already exists.")"""
        super().save(*args, **kwargs)

    @staticmethod
    def read_messages(messages, user):
        messages = messages.filter(~Q(message__sender=user))
        read_message_ids = user.readmessagelog_set.filter(message__in=messages).only("message_id").values_list("message_id", flat=True)
        messages = messages.filter(~Q(id__in=read_message_ids))
        ReadMessageLog.objects.bulk_create([
            ReadMessageLog(reader=user, message=message) for message in messages
        ])


class Message(BaseModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True)
    sender = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="sent_messages")
    job_post = models.ForeignKey(JobPost, on_delete=models.SET_NULL, null=True, default=None)
    body = models.TextField()

    def __str__(self) -> str:
        return f"{self.sender}"


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