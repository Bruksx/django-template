from ninja.errors import HttpError
import uuid
from django.db import models, router, transaction, connections
from django.core.exceptions import FieldDoesNotExist
from django.utils.functional import cached_property
from django.db.models.utils import AltersData, resolve_callables
from django.db.models import Manager, Q, signals
from django.db.models.query import QuerySet
import warnings
from django.utils.deprecation import RemovedInDjango60Warning


class Deferred:
    def __repr__(self):
        return "<Deferred field>"

    def __str__(self):
        return "<Deferred field>"


DEFERRED = Deferred()


class ModelStateFieldsCacheDescriptor:
    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        res = instance.fields_cache = {}
        return res


class ModelState:
    """Store model instance state."""
    db = None
    adding = True
    fields_cache = ModelStateFieldsCacheDescriptor()


def patched_set(self, instance, value):
    """
    Function to override Django's ForwardManyToOneDescriptor.__set__
    and ManyToManyDescriptor.__set__ default behavior
    """
    if isinstance(value, str):
        try:
            value = uuid.UUID(value, version=4)
        except ValueError:
            pass

    # Handle ForeignKey and OneToOne relationships
    if isinstance(value, uuid.UUID):
        parent_model = self.field.remote_field.model
        value = parent_model.objects.filter(uid=value).first()
        if not value:
            raise HttpError(404, f"{parent_model.__name__} not found")

    # Default ForeignKey behavior follows
    if value is not None and not isinstance(value, self.field.remote_field.model._meta.concrete_model):
        raise ValueError(
            'Cannot assign "%r": "%s.%s" must be a "%s" instance.'
            % (
                value,
                instance._meta.object_name,
                self.field.name,
                self.field.remote_field.model._meta.object_name,
            )
        )
    elif value is not None:
        if instance._state.db is None:
            instance._state.db = router.db_for_write(
                instance.__class__, instance=value
            )
        if value._state.db is None:
            value._state.db = router.db_for_write(
                value.__class__, instance=instance
            )
        if not router.allow_relation(value, instance):
            raise ValueError(
                'Cannot assign "%r": the current database router prevents this '
                "relation." % value
            )

    remote_field = self.field.remote_field

    if value is None:
        related = self.field.get_cached_value(instance, default=None)
        if related is not None:
            remote_field.set_cached_value(related, None)
        for lh_field, rh_field in self.field.related_fields:
            setattr(instance, lh_field.attname, None)
    else:
        for lh_field, rh_field in self.field.related_fields:
            setattr(instance, lh_field.attname, getattr(value, rh_field.attname))

    self.field.set_cached_value(instance, value)

    if value is not None and not remote_field.multiple:
        remote_field.set_cached_value(value, instance)