# metrics/tasks.py
from datetime import datetime

from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

from .models import APIMetric, PageMetric

ACTIVE_KEYS_KEY = "metrics:active_keys"
PAGE_ACTIVE_KEYS_KEY = "metrics:page:active_keys"

def aggregate_api_metrics():
    active_keys = cache.get(ACTIVE_KEYS_KEY) or set()
    if not active_keys:
        return

    # Clear the tracked set first so new keys during aggregation aren't lost
    cache.delete(ACTIVE_KEYS_KEY)

    for base_key in active_keys:
        try:
            parts = base_key.split(":")
            # base_key format: metrics:api:<path>:<date>
            path = parts[2]
            date_str = parts[3]
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except (IndexError, ValueError):
            continue

        count = cache.get(f"{base_key}:count", 0)
        total_time = cache.get(f"{base_key}:total_time", 0.0)

        if not count and not total_time:
            continue

        month = dt.replace(day=1).date()

        obj, _ = APIMetric.objects.get_or_create(path=path, month=month)
        APIMetric.objects.filter(id=obj.id).update(
            count=F("count") + int(count),
            total_time=F("total_time") + float(total_time),
            updated_at=timezone.now()
        )

        cache.delete(f"{base_key}:count")
        cache.delete(f"{base_key}:total_time")

# metrics/tasks.py
def aggregate_page_metrics():
    active_keys = cache.get(PAGE_ACTIVE_KEYS_KEY) or set()
    if not active_keys:
        return

    cache.delete(PAGE_ACTIVE_KEYS_KEY)

    for base_key in active_keys:
        try:
            # base_key format: metrics:page:<path>:<YYYY-MM>
            parts = base_key.split(":")
            path = parts[2]
            dt = datetime.strptime(parts[3], "%Y-%m")
            month = dt.replace(day=1).date()
        except (IndexError, ValueError):
            continue

        count = cache.get(f"{base_key}:count", 0)
        total_time = cache.get(f"{base_key}:total_time", 0.0)

        if not count and not total_time:
            continue

        obj, _ = PageMetric.objects.get_or_create(path=path, month=month)
        PageMetric.objects.filter(id=obj.id).update(
            count=F("count") + int(count),
            total_time=F("total_time") + float(total_time),
            updated_at=timezone.now()
        )

        cache.delete(f"{base_key}:count")
        cache.delete(f"{base_key}:total_time")