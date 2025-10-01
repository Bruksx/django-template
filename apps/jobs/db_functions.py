from django.db.models import Func


class Epoch(Func):
    function = "EXTRACT"
    template = "%(function)s(EPOCH FROM (%(expressions)s) AT TIME ZONE 'UTC')"