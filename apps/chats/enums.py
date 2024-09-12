from core.enums import BaseEnum


class ChatMessageAttachmentType(BaseEnum):
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"