from typing import List
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django_q.tasks import async_task
from ninja import Router, PatchDict
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth

from accounts.models import User
from chats.models import Message, Conversation, ReadMessageLog, MessageAttachment
from chats.schemas import ChatListSchema, ChatMessageSchema, ChatUserSchema, ResponseSchema, MutateChatMessageSchema

# Create your views here.
router = Router(tags=["Chats"])

@router.get("", auth=JWTAuth(), response=List[ChatListSchema])
def get_chats(request, search:str=""):
    user = request.user
    queryset = Conversation.objects.filter(users__id=user.id).order_by("-last_message_time")

    if search:
        queryset = queryset.filter(Q(message__body__icontains=search)|
                                   Q(users__first_name__icontains=search)|
                                   Q(users__last_name__icontains=search)
                                   )

    return queryset

@router.get("{conversation_uid}/messages", auth=JWTAuth(), response=List[ChatMessageSchema])
@paginate(pass_parameter="pagination_info")
def get_messages(request, conversation_uid:UUID, **kwargs):
    user = request.user
    conversation = Conversation.objects.filter(users__id=user.id, uid=conversation_uid).first()
    if not conversation:
        raise HttpError(403, "Not allowed")
    pagination = kwargs.get("pagination_info")
    start = pagination.offset * pagination.limit
    end = start + pagination.limit
    queryset = Message.objects.filter(conversation__uid=conversation_uid).order_by("created_at")[start:end]
    async_task(conversation.read_messages(message_ids=list(queryset.values_list("id", flat=True)), user_id=user.id))
    return queryset


@router.get("messages/{message_uid}/read-by", auth=JWTAuth(), response=List[ChatUserSchema])
def get_chat_message_readers(request, message_uid:UUID):
    user = request.user
    if not Message.objects.filter(uid=message_uid, sender=user).exists():
        raise HttpError(403, "Not allowed")
    user_ids = ReadMessageLog.objects.filter(message__uid=message_uid).values_list("reader_id", flat=True)
    return User.objects.filter(id__in=user_ids)


@router.post("{conversation_uid}/messages", auth=JWTAuth(), response={200: ResponseSchema})
@transaction.atomic
def create_chat_message(request, conversation_uid:UUID, data: PatchDict[MutateChatMessageSchema]):
    user = request.user
    conversation = Conversation.objects.filter(uid=conversation_uid, users__id=user.id).first()
    if not conversation:
        raise HttpError(403, "Not allowed")
    attachments = data.pop("attachments", [])
    message = Message.objects.create(conversation=conversation, sender=user, **data)
    MessageAttachment.objects.bulk_create([
        MessageAttachment(message=message, file=attachment["file"], file_type=attachment["file_type"].value) for attachment in attachments
    ])
    return Response(status=200, data={"message": "Message sent successfully"})