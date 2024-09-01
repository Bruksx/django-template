from django.db import models
from core.models import BaseModel
from accounts.models import User
from jobs.models import Job


# Create your models here.
class Message(BaseModel):
    sender = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="received_messages")
    job = models.ForeignKey(Job, on_delete=models.DO_NOTHING)
    body = models.TextField()

    def __str__(self) -> str:
        return f"{self.sender} {self.receiver}"
