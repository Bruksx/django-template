from typing import List
from uuid import UUID

from django.db.models import Q
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja_jwt.authentication import JWTAuth

from accounts.models import User
from chats.models import Message, Conversation, ReadMessageLog
from chats.schemas import ChatListSchema, ChatMessageSchema, ChatUserSchema

# Create your views here.
router = Router(tags=["Chats"])

@router.get("", auth=JWTAuth(), response=List[ChatListSchema])
def get_chats(request, search:str):
    user = request.user
    queryset = Message.objects.prefetch_related("conversation").filter(conversation__users__id=user.id).distinct("conversation").order_by("-created_at")
    if search:
        queryset = queryset.filter(Q(body__icontains=search)|
                                   Q(conversation__users__first_name__icontains=search)|
                                   Q(conversation__users__last_name__icontains=search)
                                   )

    return queryset

@router.get("{conversation_uid}", auth=JWTAuth(), response=List[ChatMessageSchema])
@paginate
def get_messages(request, conversation_uid:UUID):
    user = request.user
    if not Conversation.objects.filter(users__id=user.id, uid=conversation_uid).exists():
        raise HttpError(403, "Not allowed")
    return Message.objects.filter(conversation__uid=conversation_uid).order_by("created_at")


@router.get("messages/{message_uid}/read-by", auth=JWTAuth(), response=List[ChatUserSchema])
def get_chat_message_readers(request, message_uid:UUID):
    user = request.user
    if not Message.objects.filter(uid=message_uid, conversation__users__id=user.id).exists():
        raise HttpError(403, "Not allowed")
    user_ids = ReadMessageLog.objects.filter(message__uid=message_uid).values_list("user_id", flat=True)
    return User.objects.filter(id__in=user_ids)


