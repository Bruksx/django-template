import uuid

from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor, ManyToManyDescriptor
from django_softdelete.managers import SoftDeleteManager, SoftDeleteQuerySet
from django_softdelete.models import SoftDeleteModel

from monkeypatches.patched_related_descriptors import ManyToManyDescriptor as PatchedManyToManyDescriptor
from core.patches.monkeypatches import patched_set

ForwardManyToOneDescriptor.__set__ = patched_set
ManyToManyDescriptor.related_manager_cls = PatchedManyToManyDescriptor.related_manager_cls

# Custom QuerySet class

from django.db import models
from django.db.models import ForeignKey
from uuid import UUID


class CustomQuerySet(SoftDeleteQuerySet):
    def update(self, **kwargs):
        # Iterate over the kwargs to check for ForeignKey fields
        for key, value in kwargs.items():
            # Get the model field for the key
            field = self.model._meta.get_field(key)
            if isinstance(field, ForeignKey) and isinstance(value, UUID):
                # Convert the UUID field to the corresponding instance
                related_model = field.related_model
                try:
                    related_instance = related_model.objects.get(uid=value)
                except related_model.DoesNotExist:
                    raise ValueError(f"No {related_model.__name__} found with uid {value}")
                # Replace the UUID with the actual instance's ID for update
                kwargs[key] = related_instance.pk

        # Call the original update method
        return super().update(**kwargs)


class BaseManager(SoftDeleteManager):

    def get_queryset(self):
        return CustomQuerySet(self.model, using=self._db).filter(
            deleted_at__isnull=True
        )


# Create your models here.
class BaseModel(SoftDeleteModel):
    uid = models.UUIDField(unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    objects = BaseManager()



    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.save(update_fields=kwargs.keys())
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