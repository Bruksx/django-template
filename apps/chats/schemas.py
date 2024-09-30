from typing import Optional, List
from uuid import UUID

from ninja import ModelSchema, Schema
from ninja.orm.fields import AnyObject
from pydantic import Field
from setuptools.command.alias import alias

from accounts.models import User
from accounts.schemas.common import UserSchema
from chats.enums import ChatMessageAttachmentType
from chats.models import Message, MessageAttachment
from jobs.models import JobPost


class ChatUserSchema(ModelSchema):
    photo_url : Optional[str] = None

    class Meta:
        model = User
        fields = ("uid", "email", "first_name", "last_name", "type")

    @staticmethod
    def resolve_photo_url(obj):
        if hasattr(obj, "talent"):
            return obj.talent.photo_url
        elif hasattr(obj, "businessuser"):
            return obj.businessuser.business.get_logo()
        return None

class ChatJobSchema(ModelSchema):
    country: str
    job_title: str
    job_business: str
    job_business_logo: str
    class Meta:
        model = JobPost
        fields = ("uid", "created_at")

    @staticmethod
    def resolve_job_title(obj):
        return obj.job.title

    @staticmethod
    def resolve_job_business(obj):
        return obj.job.created_by.business.name

    @staticmethod
    def resolve_job_business_logo(obj):
        return obj.job.created_by.business.get_logo()

    @staticmethod
    def resolve_country(obj):
        return obj.country.name


class ChatListSchema(ModelSchema):
    sender : ChatUserSchema
    conversation_uid: UUID
    job_post: ChatJobSchema
    read: Optional[bool] = None
    class Meta:
        model = Message
        fields = ("uid", "sender", "body", "job_post", "created_at")

    @staticmethod
    def resolve_conversation_uid(obj):
        return obj.conversation.uid

    @staticmethod
    def resolve_read(obj, context):
        request = context.get("request")
        user = request.user
        if user == obj.sender:
            return None
        return obj.readmessagelog_set.filter(user=user).exist()

class ChatAttachmentSchema(ModelSchema):
    file_url: Optional[str] = None
    class Meta:
        model = MessageAttachment
        fields = ("uid", "file_type", "created_at")

class ChatMessageSchema(ModelSchema):
    sender: ChatUserSchema
    conversation_uid: UUID
    job_post: ChatJobSchema
    read: Optional[bool] = None
    attachments: List[ChatAttachmentSchema]

    class Meta:
        model = Message
        fields = ("uid", "sender", "body", "job_post", "created_at")

    @staticmethod
    def resolve_conversation_uid(obj):
        return obj.conversation.uid

    @staticmethod
    def resolve_read(obj, context):
        request = context.get("request")
        user = request.user
        if user == obj.sender:
            return None
        return obj.readmessagelog_set.filter(user=user).exist()

    @staticmethod
    def resolve_attachments(obj):
        return obj.messageattachment_set.all()


class MutateChatAttachmentSchema(Schema):
    file: str
    file_type: ChatMessageAttachmentType

class MutateChatMessageSchema(Schema):
    job_post_uid: UUID
    attachments: List[str]
    body: str


class ResponseSchema(Schema):
    message: str
    data: Optional[AnyObject]

