from django.db import models
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


class Message(BaseModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True)
    sender = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="sent_messages")
    job_post = models.ForeignKey(JobPost, on_delete=models.DO_NOTHING)
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