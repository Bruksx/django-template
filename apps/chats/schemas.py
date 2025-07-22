from typing import Optional, List, Any, Literal
from uuid import UUID

from ninja import ModelSchema, Schema
from ninja.orm.fields import AnyObject

from accounts.models import User, Talent, BusinessUser
from chats.enums import ChatMessageAttachmentType
from chats.models import Message, MessageAttachment, Conversation
from jobs.models import JobPost
from paginations import CustomPaginatedResponseSchema as PaginatedResponseSchema

from apps.accounts.enums import UserType
from ws_tester import business_user


class ChatUserSchema(ModelSchema):
    photo_url:Optional[str] = None
    user_type_uid:Optional[UUID] = None

    class Meta:
        model = User
        fields = ("uid", "email", "first_name", "last_name", "type")

    @staticmethod
    def resolve_user_type_uid(obj):
        if obj.type == UserType.TALENT.value:
            talent = Talent.objects.filter(user=obj).first()
            if not talent:
                return
            return talent.uid
        elif obj.type == UserType.BUSINESS.value:
            business_user = BusinessUser.objects.filter(user=obj).first()
            if not business_user:
                return
            return business_user.uid
        return


    @staticmethod
    def resolve_business_user_uid(obj):
        return BusinessUser.objects.filter(user=obj).first()


class ChatJobSchema(ModelSchema):
    country: str
    job_title: str
    job_business: str
    job_business_logo: Optional[str]
    class Meta:
        model = JobPost
        fields = ("uid", "created_at")

    @staticmethod
    def resolve_job_title(obj):
        if obj.job:
            return obj.job.title
        return ""

    @staticmethod
    def resolve_job_business(obj):
        if not obj.job or not obj.job.created_by:
            return ""
        if not obj.job.created_by.business:
            return ""
        if not obj.job.created_by.business.name:
            return ""
        return obj.job.created_by.business.name

    @staticmethod
    def resolve_job_business_logo(obj):
        try:
            return obj.job.created_by.business.get_logo()
        except:
            return None

    @staticmethod
    def resolve_country(obj):
        if not obj.country:
            return ""
        return obj.country.name


class ChatMessageListSchema(ModelSchema):
    sender : ChatUserSchema
    conversation_uid: UUID
    job_post: Optional[ChatJobSchema]
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
        return obj.readers.filter(id=user.id).exist()

class ChatListSchema(ModelSchema):
    last_message : Optional[ChatMessageListSchema]
    unread_messages_count : int
    recipient: Optional[ChatUserSchema]

    class Meta:
        model = Conversation
        fields = ("uid", "locked")

    @staticmethod
    def resolve_unread_messages_count(obj, context):
        user = context.get("request").user
        return obj.unread_messages_count(user)

    @staticmethod
    def resolve_recipient(obj, context):
        user = context.get("request").user
        recipient = obj.users.exclude(id=user.id).first()
        if not recipient:
            return None
        return ChatUserSchema.from_orm(recipient)


class ChatAttachmentSchema(ModelSchema):
    file_url: Optional[str] = None
    class Meta:
        model = MessageAttachment
        fields = ("uid", "file_type", "created_at")

class ChatMessageSchema(ModelSchema):
    sender: ChatUserSchema
    conversation_uid: UUID
    job_post: Optional[ChatJobSchema]
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
        return obj.readers.filter(id=user.id).exist()

    @staticmethod
    def resolve_attachments(obj):
        return obj.messageattachment_set.all()


class MutateChatAttachmentSchema(Schema):
    file: str
    file_type: ChatMessageAttachmentType

class MutateChatMessageSchema(Schema):
    job_post: Optional[UUID] = None
    body: Optional[str] = None


class ResponseSchema(Schema):
    message: str
    data: Optional[AnyObject]

class ChatMessagePaginatedSchema(PaginatedResponseSchema[ChatMessageSchema]):
    locked: bool
    recipient: ChatUserSchema

class AttachmentSchema(Schema):
    content_type: str
    data: str
    name: str

class CreateMessageSchema(Schema):
    job_post: Optional[UUID] = None
    attachments: Optional[List[AttachmentSchema]]
    body: str


class ChatMessageRequestSchema(Schema):
    data: CreateMessageSchema|Any
    action: Literal["new_message", "is_typing", "stopped_typing", "read_message"]



class ChatMessageErrorSchema(Schema):
    message: Optional[str]=None
    data: Optional[Any]=None
    status: int


class ChatMessageResponseSchema(Schema):
    sender_id: UUID
    sender: str
    recipient: ChatUserSchema
    chat_id: UUID
    action: Literal["new_message", "is_typing", "stopped_typing", "read_message"]
    data: Optional[ChatMessageSchema|AnyObject]

