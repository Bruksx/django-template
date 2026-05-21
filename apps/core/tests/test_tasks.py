from django.test import TestCase, override_settings
from django.core.cache import cache
from datetime import date
from core.tasks import aggregate_api_metrics, ACTIVE_KEYS_KEY
from core.models import APIMetric

@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
})
class AggregateAPIMetricsTests(TestCase):
    def setUp(self):
        # Clear cache before each test
        cache.clear()

    def test_aggregate_api_metrics_no_keys(self):
        # With no keys in cache, it should return without doing anything
        aggregate_api_metrics()
        self.assertEqual(APIMetric.objects.count(), 0)

    def test_aggregate_api_metrics_success(self):
        # Setup cache data
        base_key = "metrics:api:/api/v1/users:2026-05-21"
        active_keys = {base_key}
        cache.set(ACTIVE_KEYS_KEY, active_keys)
        cache.set(f"{base_key}:count", 10)
        cache.set(f"{base_key}:total_time", 5.5)

        aggregate_api_metrics()

        # Verify APIMetric was created
        metric = APIMetric.objects.get(path="/api/v1/users", month=date(2026, 5, 1))
        self.assertEqual(metric.count, 10)
        self.assertEqual(metric.total_time, 5.5)

        # Verify cache was cleared
        self.assertIsNone(cache.get(ACTIVE_KEYS_KEY))
        self.assertIsNone(cache.get(f"{base_key}:count"))
        self.assertIsNone(cache.get(f"{base_key}:total_time"))

    def test_aggregate_api_metrics_aggregation(self):
        # Test multiple days in same month aggregate into one record
        day1_key = "metrics:api:/api/v1/users:2026-05-21"
        day2_key = "metrics:api:/api/v1/users:2026-05-22"

        active_keys = {day1_key, day2_key}
        cache.set(ACTIVE_KEYS_KEY, active_keys)

        cache.set(f"{day1_key}:count", 10)
        cache.set(f"{day1_key}:total_time", 5.0)

        cache.set(f"{day2_key}:count", 5)
        cache.set(f"{day2_key}:total_time", 2.0)

        aggregate_api_metrics()

        metric = APIMetric.objects.get(path="/api/v1/users", month=date(2026, 5, 1))
        self.assertEqual(metric.count, 15)
        self.assertEqual(metric.total_time, 7.0)

    def test_aggregate_api_metrics_invalid_key_format(self):
        # Test that invalid keys are skipped
        invalid_key = "invalid:key:format"
        active_keys = {invalid_key}
        cache.set(ACTIVE_KEYS_KEY, active_keys)

        aggregate_api_metrics()

        self.assertEqual(APIMetric.objects.count(), 0)
        self.assertIsNone(cache.get(ACTIVE_KEYS_KEY))

    def test_aggregate_api_metrics_zero_values(self):
        # If count and total_time are 0, it should be skipped
        base_key = "metrics:api:/api/v1/users:2026-05-21"
        active_keys = {base_key}
        cache.set(ACTIVE_KEYS_KEY, active_keys)
        cache.set(f"{base_key}:count", 0)
        cache.set(f"{base_key}:total_time", 0.0)

        aggregate_api_metrics()

        self.assertEqual(APIMetric.objects.count(), 0)
        self.assertIsNone(cache.get(ACTIVE_KEYS_KEY))
