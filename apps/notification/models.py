from django.db import models

from core.models import BaseModel


# Create your models here.


class Notification(BaseModel):
    # this may be removed in the future as true schema is yet to be determined
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
