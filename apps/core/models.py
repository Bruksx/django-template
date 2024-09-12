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