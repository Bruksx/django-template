import json
import logging

from accounts.enums import UserType
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from chats.enums import ChatMessageAttachmentType
from chats.models import Conversation, Message, MessageAttachment
from chats.schemas import CreateMessageSchema, ChatMessageErrorSchema, ChatMessageSchema, ChatUserSchema
from django.db import transaction
from jobs.models import JobPost

from helpers.utils import convert_base64_to_image_file


class ChatConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.group_name = None
        self.chat = None
        self.user = None
        self.recipient = None
        self.unique_id = None

    @database_sync_to_async
    def get_conversation(self):
        conversation_uid = self.scope["url_route"]["kwargs"].get("conversation_uid")
        if not conversation_uid:
            return
        return Conversation.objects.filter(uid=conversation_uid, users__id=self.user.id).first()


    async def connect(self):
        user = self.scope.get("user")
        if not user:
            await self.close()
            return
        self.user = user
        chat = await self.get_conversation()
        if not chat:
            await self.close()
            return
        self.unique_id = self.user.unique_chat_id
        recipient = await sync_to_async(lambda x: x.users.exclude(id=user.id).first())(chat)
        self.recipient = recipient
        self.group_name = chat.chat_group_name
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add(self.unique_id, self.channel_name)
        await self.accept()
        self.chat = chat
        await self.send(f"{self.user} just connected to {recipient} chat")

    async def disconnect(self, code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            self.group_name = None
        self.user = None
        await super().disconnect(code)

    async def websocket_receive(self, data):
        data = json.loads(data["text"])
        if len(data) == 2 and data["action"] == "new_message":
            logging.critical("about to send")
            await self.send_chat_message(data["data"])
        else:
            await self.channel_layer.group_send(
                self.group_name, {"type": "notify", "data": json.dumps(data)}
            )

    async def notify(self, event):
        data = json.loads(event["data"])
        event["data"] = json.dumps(data)
        await self.send(text_data=event["data"])

    async def error(self, event):
        data = json.loads(event["data"])
        event["data"] = json.dumps(data)
        await self.send(text_data=event["data"])

    async def send_chat_message(self, body: CreateMessageSchema):
        recipient = await sync_to_async(self.chat.users.exclude)(id=self.user.id)
        recipient = await sync_to_async(recipient.first)()
        if self.user.type == UserType.TALENT.value and recipient.type == UserType.TALENT.value:
            error = ChatMessageErrorSchema(message="Talent cannot message talent", status=403).dict()
            await self.channel_layer.group_send(
                self.unique_id, {"type": "error", "data": json.dumps(error)}
            )

        message_count = await sync_to_async(self.chat.message_set.count)()
        if message_count == 0 and self.user.type == UserType.TALENT.value and recipient.type == UserType.BUSINESS.value:
            error = ChatMessageErrorSchema(message="Talent cannot start the conversation", status=403).dict()
            await self.channel_layer.group_send(
                self.unique_id, {"type": "error", "data": json.dumps(error)}
            )
            return
        if self.chat.locked and self.user.type == UserType.TALENT.value and recipient.type == UserType.BUSINESS.value:
            error = ChatMessageErrorSchema(status=403, message="Conversation is locked").dict()
            await self.channel_layer.group_send(
                self.unique_id, {"type": "error", "data": json.dumps(error)}
            )
            return
        if recipient.type == UserType.BUSINESS.value and self.user.type == UserType.BUSINESS.value:
            error = ChatMessageErrorSchema(status=403, message="Business user cannot message business user").dict()
            await self.channel_layer.group_send(
                self.unique_id, {"type": "error", "data": json.dumps(error)}
            )
            return
        job_post = None
        if body.get("job_post"):
            job_post = await sync_to_async(JobPost.objects.filter)(uid=body["job_post"])
            job_post = await sync_to_async(job_post.first)()
            if not job_post:
                error = ChatMessageErrorSchema(status=400, message="This job does not exist").dict()
                await self.channel_layer.group_send(
                    self.unique_id, {"type": "error", "data": json.dumps(error)}
                )

                return
        message, data = await self.create_chat_message(body.get("body"),job_post, body.get("attachments"))
        await sync_to_async(message.handle_post_save)(notify=False)
        await sync_to_async(self.chat.refresh_from_db)()
        recipient = await sync_to_async(ChatUserSchema.from_orm)(self.recipient)
        recipient = json.loads(recipient.model_dump_json())
        data = dict(
            sender_id=str(self.user.uid),
            sender=self.user.fullname,
            recipient=recipient,
            chat_id=str(self.chat.uid),
            action="new_message",
            data=data)
        await self.channel_layer.group_send(
            self.group_name, {"type": "notify", "data": json.dumps(data)}
        )

    @database_sync_to_async
    def create_chat_message(self, body, job_post, attachments):
        with transaction.atomic():
            message = Message.objects.create(conversation=self.chat, sender=self.user, body=body, job_post=job_post)
            if attachments:
                message_attachments = list()
                for attachment in attachments:
                    attachment_obj = convert_base64_to_image_file(attachment["data"], attachment["name"])
                    content_type = attachment["content_type"].split("/")[-1] if "/" in attachment["content_type"] else attachment["content_type"]
                    if content_type in ("jpg", "jpeg", "gif", "png"):
                        file_type = ChatMessageAttachmentType.IMAGE.value
                    elif content_type in ("mp3", "ogg", "mpeg", "wav"):
                        file_type = ChatMessageAttachmentType.AUDIO.value
                    elif content_type in ("mp4", "3gp"):
                        file_type = ChatMessageAttachmentType.VIDEO.value
                    else:
                        file_type = ChatMessageAttachmentType.DOCUMENT.value
                    message_attachments.append(MessageAttachment(message=message, file=attachment_obj, file_type=file_type))
                MessageAttachment.objects.bulk_create(message_attachments)
            return message, json.loads(ChatMessageSchema.from_orm(message).model_dump_json())



