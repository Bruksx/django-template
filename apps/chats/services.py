from accounts.models import Talent
from chats.enums import ChatMessageAttachmentType
from chats.models import Conversation, Message, MessageAttachment


def send_bulk_chat_message(talent_uids,  message, business_user_id, attachments):
    talents = Talent.objects.select_related("user").filter(uid__in=talent_uids).only("user_id", "user__fullname")
    business_user_chats = Conversation.objects.filter(users__id=business_user_id)
    msgs = list()
    for talent in talents:
        chat = business_user_chats.filter(users__id=talent.user_id).first()
        if not chat:
            chat = Conversation.objects.create()
            chat.users.add(business_user_id, talent.user_id)
            chat.save()
        msgs.append(
            Message(conversation=chat, sender_id=business_user_id, body=message, job_post=None)
        )
    msgs = Message.objects.bulk_create(msgs)

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
        for msg in msgs:
            message_attachments.append(MessageAttachment(message=msg, file=attachment, file_type=file_type))
    MessageAttachment.objects.bulk_create(message_attachments)
    return
