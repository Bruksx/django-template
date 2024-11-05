from uuid import UUID

from typing_extensions import TypedDict, Literal


class NotificationSchema(TypedDict):
    # to be sent via ws
    entity: Literal["chat", ] # can add more entities
    entity_id: UUID
    entity_str: str
    action: Literal["new", "update", "delete", "add"] # can add more actions
    title: str
    description: str

    # db types
    recipient_ids: list[UUID]
    recipient_types: Literal["talent", "business", "all"]
    viewers : list[UUID]



