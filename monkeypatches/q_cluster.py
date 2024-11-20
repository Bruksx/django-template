import sys

from django_q.tasks import async_task as django_async_task


def async_task(func, *args, **kwargs):
    if "test" in sys.argv:
        """ to enable it run synchronously in tests """
        return func(*args, **kwargs)
    return django_async_task(func, *args, **kwargs)


