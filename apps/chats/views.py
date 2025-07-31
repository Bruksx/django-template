from typing import List
from uuid import UUID

from config.permissions import IsBusinessUser
from django.db import transaction
from django.db.models import Q, F, OrderBy, Case, When, Value, IntegerField
from monkeypatches.q_cluster import async_task
from monkeypatches.response import Response
from ninja import Router, UploadedFile, Form
from ninja.errors import HttpError
from ninja_extra.pagination import paginate
from ninja_jwt.authentication import JWTAuth

from accounts.enums import UserType
from accounts.models import User
from chats.enums import ChatMessageAttachmentType
from chats.models import Message, Conversation, MessageAttachment
from chats.schemas import ChatListSchema, ChatUserSchema, ResponseSchema, MutateChatMessageSchema, \
    ChatMessagePaginatedSchema, ChatMessageRequestSchema, ChatMessageResponseSchema, ChatMessageErrorSchema
from jobs.business_views import pagination_class
from paginations import CustomPageNumberPaginationExtra as PageNumberPaginationExtra
from paginations import CustomPaginatedResponseSchema as PaginatedResponseSchema

# Create your views here.
router = Router(tags=["Chats"])
ws_router = Router(tags=["Websocket"])


@router.get("", auth=JWTAuth(), response=PaginatedResponseSchema[ChatListSchema])
@paginate(PageNumberPaginationExtra, page_size=50)
def get_chats(request, search:str=""):
    user = request.user
    queryset = Conversation.objects.prefetch_related("users").filter(users__id=user.id).annotate(
        null_order=Case(
            When(last_message_time__isnull=True, then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).order_by('null_order', '-last_message_time')

    if search:
        q = Q()
        for s in search.split(" "):
            if s:
                q = q | Q(users__fullname__icontains=s) | Q(message_body__icontains=s)
        queryset = queryset.filter(q)

    return queryset.distinct()

@router.get("{conversation_uid}/messages", auth=JWTAuth(), response=ChatMessagePaginatedSchema)
def get_messages(request, conversation_uid:UUID, page_size=50, page=1, **kwargs):
    user = request.user
    conversation = Conversation.objects.filter(users__id=user.id, uid=conversation_uid).first()
    if not conversation:
        raise HttpError(403, "Not allowed")
    queryset = Message.objects.prefetch_related("messageattachment_set").filter(conversation__uid=conversation_uid).order_by("-created_at")
    async_task(conversation.read_messages, message_ids=list(queryset.values_list("id", flat=True)), user_id=user.id)
    pagination = pagination_class(page_size).Input(page=page, page_size=page_size)
    return pagination_class(page_size).paginate_queryset(
        queryset=queryset,
        request=request,
        pagination=pagination,
        locked=conversation.locked,
        recipient=ChatUserSchema.from_orm(conversation.get_recipient(user)).__dict__
    )

@router.get("messages/{message_uid}/read-by", auth=JWTAuth(), response=List[ChatUserSchema])
def get_chat_message_readers(request, message_uid:UUID):
    user = request.user
    message = Message.objects.filter(uid=message_uid, sender=user).first()
    if not message:
        raise HttpError(404, "This message does not exist")
    return message.readers.all()


@router.post("{conversation_uid}/messages", auth=JWTAuth(), response={200: ResponseSchema})
@transaction.atomic
def create_chat_message(request, conversation_uid:UUID,
                       body: MutateChatMessageSchema = Form(),  attachments: List[UploadedFile]=None):
    user = request.user
    conversation = Conversation.objects.filter(uid=conversation_uid, users__id=user.id).first()
    if not conversation:
        raise HttpError(404, "This conversation does not exist")
    recipient = conversation.users.exclude(id=user.id).first()
    if user.type == UserType.TALENT.value and recipient.type == UserType.TALENT.value:
        raise HttpError(403, "Not allowed")
    if conversation.message_set.count() == 0 and user.type == UserType.TALENT.value and recipient.type == UserType.BUSINESS.value:
        raise HttpError(403, "Not allowed")
    if conversation.locked and user.type == UserType.TALENT.value and recipient.type == UserType.BUSINESS.value:
        raise HttpError(403, "Conversation is locked")
    if recipient.type == UserType.BUSINESS.value and user.type == UserType.BUSINESS.value:
        raise HttpError(403, "Not allowed")
    message = Message.objects.create(conversation=conversation, sender=user, body=body.body, job_post=body.job_post)
    async_task(message.handle_post_save, notify=True)
    if attachments:
        message_attachments = list()
        for attachment in attachments:
            content_type = attachment.content_type.split("/")[-1]
            if content_type in ("jpg", "jpeg", "gif", "png"):
                file_type = ChatMessageAttachmentType.IMAGE.value
            elif content_type in ("mp3", "ogg", "mpeg", "wav"):
                file_type = ChatMessageAttachmentType.AUDIO.value
            elif content_type in ("mp4", "3gp"):
                file_type = ChatMessageAttachmentType.VIDEO.value
            else:
                file_type = ChatMessageAttachmentType.DOCUMENT.value
            message_attachments.append(MessageAttachment(message=message, file=attachment, file_type=file_type))
        MessageAttachment.objects.bulk_create(message_attachments)
    return Response(status=200, data={"message": "Message sent successfully"})


@router.post("{conversation_uid}/lock", auth=JWTAuth(), response={200: ChatListSchema})
@transaction.atomic
def lock_conversation(request, conversation_uid:UUID, lock:bool):
    IsBusinessUser.check(request)
    conversation = Conversation.objects.filter(uid=conversation_uid).first()
    if not conversation:
        raise HttpError(404, "This conversation does not exist")
    if not conversation.users.filter(id=request.user.id).exists():
        raise HttpError(403, "You are not a member of this conversation")
    conversation.locked = lock
    conversation.save()
    return conversation



@router.post("users/{user_id}/start-conversation", auth=JWTAuth(), response={200: ChatListSchema})
@transaction.atomic
def start_conversation(request, user_id:UUID):
    from notification.notifications import send_new_chat_notification
    user = request.user
    if user.id == user_id:
        raise HttpError(403, "Not allowed")
    recipient = User.objects.filter(uid=user_id).first()
    if not recipient:
        raise HttpError(404, "User not found")
    if not recipient.type:
        raise HttpError(400, "This user type is invalid")

    if recipient.type == UserType.TALENT.value and user.type == UserType.TALENT.value:
        raise HttpError(403, "Not allowed")
    if recipient.type == UserType.BUSINESS.value and user.type == UserType.BUSINESS.value:
        raise HttpError(403, "Not allowed")
    if recipient.type == UserType.BUSINESS.value and user.type == UserType.TALENT.value:
        raise HttpError(403, "Not allowed")
    conversation = Conversation.objects.filter(users__id=user.id).filter(users__id=recipient.id).first()
    if conversation:
        return conversation
    conversation = Conversation.objects.create()
    conversation.users.add(user, recipient)
    conversation.save()
    async_task(send_new_chat_notification,conversation)
    return conversation


@ws_router.post('ws/chats/{conversation_uid}/', response={200: ChatMessageResponseSchema, 400: ChatMessageErrorSchema,
                                             403: ChatMessageErrorSchema, 404: ChatMessageErrorSchema},
             tags=["Websocket"])
def websocket_send_chat(request, conversation_uid:UUID, token: str, data: ChatMessageRequestSchema):
    return Response(status=200, data={"message": "Message sent successfully"})

