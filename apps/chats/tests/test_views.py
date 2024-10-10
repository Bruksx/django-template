from django.test import TestCase
from ninja.testing import TestClient

from accounts.models import User, Talent, BusinessUser, Business
from chats.models import Conversation, Message
from chats.views import router


class ChatTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email='testuser@mail.com', password='testpass',
                                             is_active=True, email_verified=True)

        self.user2 = User.objects.create_user(email='testuser2@mail.com', password='testpass',
                                             is_active=True, email_verified=True)
        self.user3 = User.objects.create_user(email='testuser3@mail.com', password='testpass',
                                             is_active=True, email_verified=True)
        self.talent = Talent.objects.create(user=self.user)
        business = Business.objects.create(name="Test Business", created_by=self.user)
        self.business_user = BusinessUser.objects.create(user=self.user2, business=business)
        self.business_user2 = BusinessUser.objects.create(user=self.user3, business=business)
        conversation = Conversation.objects.create()
        conversation.users.set([self.user, self.user2])
        conversation.save()
        self.conversation = conversation
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            body="test message",
        )
        conversation2 = Conversation.objects.create()
        conversation2.users.set([self.user, self.user3])
        conversation2.save()
        self.conversation2 = conversation2
        self.message2 = Message.objects.create(
            conversation=self.conversation2,
            sender=self.user3,
            body="test message II",
        )
        self.message3 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            body="test message III",
        )

    def test_get_chats(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["last_message"]["uid"], str(self.message3.uid))
        self.assertEqual(data[0]["unread_messages_count"], 1)

    def test_get_chat_messages(self):
        headers = {
            "authorization": f"bearer {self.user2.token}"
        }
        self.assertEqual(self.user2.readmessagelog_set.count(), 0)
        response = self.client.get(f"{str(self.conversation.uid)}/messages", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["uid"], str(self.message3.uid))
        # # test to check read message count
        # self.user3.refresh_from_db()
        # self.assertEqual(self.user2.readmessagelog_set.count(), 1)

    def test_get_chat_message_readers(self):
        # user2 reads the messages
        headers = {
            "authorization": f"bearer {self.user2.token}"
        }
        response = self.client.get(f"{str(self.conversation.uid)}/messages", headers=headers)
        self.assertEqual(response.status_code, 200)
        # user checks those who read a message
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get(f"messages/{str(self.message3.uid)}/read-by", headers=headers)
        self.assertEqual(response.status_code, 200)
        # its happening in background
        # data = response.json()
        # self.assertEqual(len(data), 1)
        # self.assertEqual(data[0]["uid"], str(self.user2.uid))

    def test_create_chat_message(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        user_message_count = self.user.message_set.count()
        data = {
            "body": "Test Body"
        }
        response = self.client.post(f"{str(self.conversation.uid)}/messages",
                                    headers=headers,
                                    json=data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertGreater(self.user.message_set.count(), user_message_count)