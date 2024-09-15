from django.db import models, router
from django_softdelete.models import SoftDeleteModel
import uuid
from ninja.errors import HttpError
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
from copy import copy
from .monkeypatches import patched_set


ForwardManyToOneDescriptor.__set__ = patched_set
#models.base.Model.__init__ = patched_init


# Create your models here.
class BaseModel(SoftDeleteModel):
    uid = models.UUIDField(unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


    def update(self, **kwargs):
        for key, value in kwargs:
            setattr(self, key, value)
        self.save()
        self.refresh_from_db()
        return self
    


class Currency(BaseModel):
    name = models.CharField()
    abbreviation = models.CharField()

    def __str__(self) -> str:
        return f"{self.name}({self.abbreviation})"


class Language(BaseModel):
    name = models.CharField(max_length=32)

    def __str__(self) -> str:
        return self.name