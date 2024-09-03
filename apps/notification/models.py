from django.db import models

from apps.accounts.models import User
from apps.core.models import BaseModel


# Create your models here.


class Notification(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
