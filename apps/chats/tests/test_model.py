from django.test import TestCase
from ninja.testing import TestClient

from accounts.models import BusinessUser, User, Talent, Business
from chats.models import Conversation, Message
from chats.views import router


class TestChatModel(TestCase):

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

    def test_read_message(self):
        unread_msg_count = self.conversation.unread_messages_count(self.user)
        self.assertEqual(unread_msg_count, 1)
        message_ids = [self.message.id, self.message3.id]
        self.conversation.read_messages(message_ids=message_ids, user_id=self.user.id)
        self.user.refresh_from_db()
        unread_msg_count = self.conversation.unread_messages_count(self.user)
        self.assertEqual(unread_msg_count, 0)

