from django.test import TestCase
from ninja.testing import TestClient

from factories import BusinessUserFactory, NotificationFactory, TalentFactory
from notification.enums import NotificationGroup
from notification.models import BusinessUserNotificationSettings, Notification
from notification.views import router


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

class GetNotificationsTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.talent = TalentFactory.create()
        self.business_user = BusinessUserFactory.create()
        self.user = self.business_user.user
        self.url = ""
        NotificationFactory.create_batch(5,
            business=self.business_user.business,
            role=self.business_user.role,
            recipient_groups=[NotificationGroup.BUSINESS_USERS.value]
        )

    def test_get_notifications(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 5)

    def test_by_another_business_user(self):
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_by_talent(self):
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_when_talent_is_recipient(self):
        notification = Notification.objects.first()
        notification.recipient_users.add(self.talent.user)
        notification.all_recipients.add(self.talent.user)
        notification.save()
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_when_business_user_is_recipient(self):
        notification = Notification.objects.first()
        business_user = BusinessUserFactory.create()
        notification.recipient_users.add(business_user.user)
        notification.all_recipients.add(business_user.user)
        notification.save()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_when_recipient_group_is_for_talent(self):
        Notification.objects.create(
            recipient_groups=[NotificationGroup.TALENTS.value]
        )
        headers = {
            "authorization": f"bearer {self.talent.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_when_recipient_group_is_for_business_user(self):
        business_user = BusinessUserFactory.create()
        NotificationFactory.create(
            business=business_user.business,
            role=business_user.role,
            recipient_groups = [NotificationGroup.BUSINESS_USERS.value]
        )
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

class DeleteNotificationsTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.user = self.business_user.user
        self.url = ""
        NotificationFactory.create_batch(5,
            business=self.business_user.business,
            role=self.business_user.role
        )

    def delete_notifications(self,user, notification_ids):
        headers = {
            "authorization": f"bearer {user.token}"
        }
        response = self.client.delete(self.url, headers=headers, json=dict(uids=notification_ids))
        print(response.content)
        self.assertEqual(response.status_code, 204)
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_when_talent_is_recipient(self):
        notification = Notification.objects.first()
        talent = TalentFactory.create()
        notification.recipient_users.add(talent.user)
        notification.all_recipients.add(talent.user)
        notification.save()
        headers = {
            "authorization": f"bearer {talent.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        self.delete_notifications(talent.user, [str(notification.uid)])

    def test_when_business_user_is_recipient(self):
        notification = Notification.objects.first()
        business_user = BusinessUserFactory.create()
        notification.recipient_users.add(business_user.user)
        notification.all_recipients.add(business_user.user)
        notification.save()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        self.delete_notifications(business_user.user, [str(notification.uid)])

    def test_when_recipient_group_is_for_talent(self):
        talent = TalentFactory.create()
        notification = Notification.objects.create(
            recipient_groups=[NotificationGroup.TALENTS.value]
        )
        headers = {
            "authorization": f"bearer {talent.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        self.delete_notifications(talent.user, [str(notification.uid)])

    def test_when_recipient_group_is_for_business_user(self):
        business_user = BusinessUserFactory.create()
        notification = NotificationFactory.create(
            business=business_user.business,
            role=business_user.role,
            recipient_groups = [NotificationGroup.BUSINESS_USERS.value]
        )
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        self.delete_notifications(business_user.user, [str(notification.uid)])



class ReadNotificationTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.business_user = BusinessUserFactory.create()
        self.user = self.business_user.user
        self.notification = NotificationFactory.create(
             recipient_groups=[
                 NotificationGroup.ALL_USERS.value
             ]
        )
        self.url = lambda uid: f"{uid}/read"

    def test_read_notification(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        self.assertFalse(self.notification.viewers.filter(id=self.user.id).exists())
        response = self.client.patch(self.url(self.notification.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Notification marked as read")
        notification = Notification.objects.filter(uid=self.notification.uid).first()
        self.assertTrue(notification.viewers.filter(id=self.user.id).exists())

    def test_by_talent_for_wrong_recipient_group(self):
        self.notification.update(recipient_groups=[NotificationGroup.BUSINESS_USERS.value])
        talent = TalentFactory.create()
        headers = {
            "authorization": f"bearer {talent.user.token}"
        }
        response = self.client.patch(self.url(self.notification.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.viewers.filter(id=self.user.id).exists())

    def test_by_business_user_for_talent_group(self):
        self.notification.update(recipient_groups=[NotificationGroup.TALENTS.value])
        business_user = BusinessUserFactory.create()
        headers = {
            "authorization": f"bearer {business_user.user.token}"
        }
        response = self.client.patch(self.url(self.notification.uid), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.viewers.filter(id=self.user.id).exists())



