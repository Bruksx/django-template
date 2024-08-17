from django.db import models
from django_softdelete.models import SoftDeleteModel
import uuid


# Create your models here.
class BaseModel(SoftDeleteModel):
    uid = models.UUIDField(unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True