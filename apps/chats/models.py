from django.db import models
from core.models import BaseModel
from accounts.models import User
from jobs.models import Job


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
    receiver = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="received_messages")
    job = models.ForeignKey(Job, on_delete=models.DO_NOTHING)
    body = models.TextField()
    is_read = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.sender} {self.receiver}"
