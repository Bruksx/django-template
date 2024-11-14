from django.test import TestCase
from ninja.testing import TestClient

from factories import BusinessUserFactory
from .models import BusinessUserNotificationSettings
from .views import router

# Create your tests here.


class GetNotificationSettingsTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        business_user = BusinessUserFactory.create()
        self.user = business_user.user
        self.url = "business/notification-settings"

    def test_get_notification_settings(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("applicants_notification", data)
        self.assertIn("matching_notification", data)
        self.assertIn("sharing_notification", data)
        self.assertIn("performance_notification", data)



class UpdateNotificationSettingsTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.user = self.business_user.user
        self.url = "business/notification-settings"

    def test_update_notification_settings(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        body = {
            "applicants_notification": False,
            "matching_notification": False,
            "sharing_notification": False,
            "performance_notification": False,
        }
        settings = BusinessUserNotificationSettings.objects.filter(business_user=self.business_user).first()
        self.assertTrue(settings.applicants_notification)
        self.assertTrue(settings.matching_notification)
        self.assertTrue(settings.sharing_notification)
        self.assertTrue(settings.performance_notification)
        response = self.client.patch(self.url, headers=headers, json=body)
        settings.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(settings.applicants_notification)
        self.assertFalse(settings.matching_notification)
        self.assertFalse(settings.sharing_notification)
        self.assertFalse(settings.performance_notification)
