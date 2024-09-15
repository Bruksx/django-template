from ninja.errors import HttpError
import uuid
from django.db import models, router
from django.db.models import base, NOT_PROVIDED
from django.db.models.signals import pre_init, post_init
from django.db.models.fields.related import ForeignObjectRel
from django.core.exceptions import FieldDoesNotExist


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
    # If true, uniqueness validation checks will consider this a new, unsaved
    # object. Necessary for correct validation of new instances of objects with
    # explicit (non-auto) PKs. This impacts validation only; it has no effect
    # on the actual save.
    adding = True
    fields_cache = ModelStateFieldsCacheDescriptor()



def patched_set(self, instance, value):
    """
    function to overide django's ForwardManyToOneDescriptor.__set__ default behavior
    """
    if isinstance(value, str):
        try:
            value = uuid.UUID(value, version=4)
        except ValueError:
            pass
    if isinstance(value, uuid.UUID):
        parent_model = self.field.remote_field.model
        value = parent_model.objects.filter(uid=value).first()
        if not value:
            raise HttpError(404, f"{parent_model.__name__} not found")
        
    #From here, copied from django's source code
    # An object must be an instance of the related class.
    if value is not None and not isinstance(
        value, self.field.remote_field.model._meta.concrete_model
    ):
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
    # If we're setting the value of a OneToOneField to None, we need to clear
    # out the cache on any old related object. Otherwise, deleting the
    # previously-related object will also cause this object to be deleted,
    # which is wrong.
    if value is None:
        # Look up the previously-related object, which may still be available
        # since we've not yet cleared out the related field.
        # Use the cache directly, instead of the accessor; if we haven't
        # populated the cache, then we don't care - we're only accessing
        # the object to invalidate the accessor cache, so there's no
        # need to populate the cache just to expire it again.
        related = self.field.get_cached_value(instance, default=None)

        # If we've got an old related object, we need to clear out its
        # cache. This cache also might not exist if the related object
        # hasn't been accessed yet.
        if related is not None:
            remote_field.set_cached_value(related, None)

        for lh_field, rh_field in self.field.related_fields:
            setattr(instance, lh_field.attname, None)

    # Set the values of the related field.
    else:
        for lh_field, rh_field in self.field.related_fields:
            setattr(instance, lh_field.attname, getattr(value, rh_field.attname))

    # Set the related instance cache used by __get__ to avoid an SQL query
    # when accessing the attribute we just set.
    self.field.set_cached_value(instance, value)

    # If this is a one-to-one relation, set the reverse accessor cache on
    # the related object to the current instance to avoid an extra SQL
    # query if it's accessed later on.
    if value is not None and not remote_field.multiple:
        remote_field.set_cached_value(value, instance)