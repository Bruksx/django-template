from datetime import timedelta

from django.utils import timezone
from helpers.utils import delete_s3_item


def delete_old_exports(days=7):
    """
    Delete old exports
    """
    from core.models import Exports
    date_of_creation = timezone.now() - timedelta(days=days)
    exports = Exports.objects.filter(created_at__lt=date_of_creation)
    for export in exports:
        delete_s3_item(export.file.url)
    exports.hard_delete()
