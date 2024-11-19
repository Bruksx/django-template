import logging
from uuid import UUID

from django.test import TestCase
from ninja.testing import TestClient

from accounts.models import User, Talent, BusinessUser, Business
from chats.models import Conversation, Message
from chats.views import router


class TestGetChatEndpoints(TestCase):
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
        response = self.client.get(f"{str(self.conversation.uid)}/messages", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["uid"], str(self.message3.uid))


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

class StartConversationTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email='testuser@mail.com', password='testpass',
                                             is_active=True, email_verified=True)

        self.user2 = User.objects.create_user(email='testuser2@mail.com', password='testpass',
                                             is_active=True, email_verified=True)
        self.talent = Talent.objects.create(user=self.user)
        self.business = Business.objects.create(name="Test Business", created_by=self.user)
        self.business_user = BusinessUser.objects.create(user=self.user2, business=self.business)

    def test_start_conversation(self):
        headers = {
            "authorization": f"bearer {self.user2.token}"
        }
        data = {
            "body": "Test Body"
        }
        conversation = Conversation.objects.filter(users__id=self.user2.id).filter(users__id=self.user2.id).first()
        self.assertIsNone(conversation)

        response = self.client.post(f"users/{self.user.uid}/start-conversation",
                                    headers=headers,
                                    json=data)
        self.assertEqual(response.status_code, 200)

        conversation = Conversation.objects.filter(users__id=self.user2.id).filter(users__id=self.user2.id).first()
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.message_set.count(), 1)

    def test_start_conversation_with_self(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
            "body": "Test Body"
        }
        conversation = Conversation.objects.filter(users__id=self.user.id).filter(users__id=self.user.id).first()
        self.assertIsNone(conversation)

        response = self.client.post(f"users/{self.user.uid}/start-conversation",
                                    headers=headers,
                                    json=data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Not allowed")

    def test_wrong_recipient_id(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
            "body": "Test Body"
        }
        conversation = Conversation.objects.filter(users__id=self.user.id).filter(users__id=self.user2.id).first()
        self.assertIsNone(conversation)

        response = self.client.post(f"users/{UUID('00000000-0000-0000-0000-000000000000')}/start-conversation",
                                    headers=headers,
                                    json=data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "User not found")

    def test_start_conversation_from_talent_to_talent(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
            "body": "Test Body"
        }
        user = User.objects.create_user(email='testuser3@mail.com', password='testpass',
                                             is_active=True, email_verified=True)

        Talent.objects.create(user=user)

        response = self.client.post(f"users/{user.uid}/start-conversation",
                                    headers=headers,
                                    json=data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Not allowed")

    def test_start_conversation_from_business_to_business(self):
        headers = {
            "authorization": f"bearer {self.user2.token}"
        }
        data = {
            "body": "Test Body"
        }
        user = User.objects.create_user(email='testuser4@mail.com', password='testpass',
                                             is_active=True, email_verified=True)

        BusinessUser.objects.create(user=user, business=self.business)

        response = self.client.post(f"users/{user.uid}/start-conversation",
                                    headers=headers,
                                    json=data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Not allowed")

    def test_existing_conversation(self):
        headers = {
            "authorization": f"bearer {self.user2.token}"
        }
        data = {
            "body": "Test Body"
        }
        response = self.client.post(f"users/{self.user.uid}/start-conversation",
                                    headers=headers,
                                    json=data)
        self.assertEqual(response.status_code, 200)
        conversation = Conversation.objects.create()
        conversation.users.set([self.user, self.user2])
        conversation.save()
        response = self.client.post(f"users/{self.user.uid}/start-conversation",
                                    headers=headers,
                                    json=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Conversation already exists")

class CreateMessageTest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(email='testuser@mail.com', password='testpass',
                                             is_active=True, email_verified=True)

        self.user2 = User.objects.create_user(email='testuser2@mail.com', password='testpass',
                                             is_active=True, email_verified=True)
        self.talent = Talent.objects.create(user=self.user)
        self.business = Business.objects.create(name="Test Business", created_by=self.user)
        self.business_user = BusinessUser.objects.create(user=self.user2, business=self.business)

    def test_create_message(self):
        headers = {
            "authorization": f"bearer {self.user2.token}"
        }
        data = {
            "body": "Test Body"
        }
        conversation = Conversation.objects.create()
        conversation.users.set([self.user, self.user2])
        conversation.save()
        response = self.client.post(f"{str(conversation.uid)}/messages",
                                    headers=headers,
                                    data=data, format="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(conversation.message_set.count(), 1)

    def test_wrong_conversation_id(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
            "body": "Test Body"
        }
        response = self.client.post(f"{UUID('00000000-0000-0000-0000-000000000000')}/messages",
                                    headers=headers,
                                    data=data, format="multipart/form-data")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "This conversation does not exist")

    def test_message_from_talent_to_talent(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
            "body": "Test Body"
        }
        user = User.objects.create_user(email='testuser3@mail.com', password='testpass',
                                        is_active=True, email_verified=True)

        Talent.objects.create(user=user)
        conversation = Conversation.objects.create()
        conversation.users.set([self.user, user])
        conversation.save()

        response = self.client.post(f"{conversation.uid}/messages",
                                    headers=headers,
                                    data=data, format="multipart/form-data")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Not allowed")

    def test_first_message_from_talent_to_business(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
            "body": "Test Body"
        }
        user = User.objects.create_user(email='testuser3@mail.com', password='testpass',
                                        is_active=True, email_verified=True)

        BusinessUser.objects.create(user=user, business=self.business)
        conversation = Conversation.objects.create()
        conversation.users.set([self.user, user])
        conversation.save()

        response = self.client.post(f"{conversation.uid}/messages",
                                    headers=headers,
                                    data=data, format="multipart/form-data")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Not allowed")

    def test_next_message_from_talent_to_business(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
            "body": "Test Body"
        }
        user = User.objects.create_user(email='testuser3@mail.com', password='testpass',
                                        is_active=True, email_verified=True)

        BusinessUser.objects.create(user=user, business=self.business)
        conversation = Conversation.objects.create()
        conversation.users.set([self.user, user])
        conversation.save()
        Message.objects.create(conversation=conversation, sender=self.user2, body="Test Body")

        response = self.client.post(f"{conversation.uid}/messages",
                                    headers=headers,
                                    data=data, format="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(conversation.message_set.count(), 2)

    def test_message_from_talent_to_locked_business_chat(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        data = {
            "body": "Test Body"
        }
        user = User.objects.create_user(email='testuser3@mail.com', password='testpass',
                                        is_active=True, email_verified=True)

        BusinessUser.objects.create(user=user, business=self.business)
        conversation = Conversation.objects.create(locked=True)
        conversation.users.set([self.user, user])
        conversation.save()
        Message.objects.create(conversation=conversation, sender=self.user2, body="Test Body")

        response = self.client.post(f"{conversation.uid}/messages",
                                    headers=headers,
                                    data=data, format="multipart/form-data")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Conversation is locked")



    def test_message_from_business_to_business(self):
        headers = {
            "authorization": f"bearer {self.user2.token}"
        }
        data = {
            "body": "Test Body"
        }
        user = User.objects.create_user(email='testuser4@mail.com', password='testpass',
                                        is_active=True, email_verified=True)

        BusinessUser.objects.create(user=user, business=self.business)

        conversation = Conversation.objects.create()
        conversation.users.set([self.user2, user])
        conversation.save()
        response = self.client.post(f"{conversation.uid}/messages",
                                    headers=headers,
                                    data=data, format="multipart/form-data")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Not allowed")