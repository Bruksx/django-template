from typing import List, Optional
from uuid import UUID

from ninja import ModelSchema, Schema
from pydantic import EmailStr

from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS
from settings.enums import PlaceHolderType
from settings.models import EmailTemplate, EmailTemplateAttachment, WorkFlowStage


class MutateEmailTemplateSchema(ModelSchema):
    sender: EmailStr
    placeholders: List[PlaceHolderType]
    bcc: List[EmailStr]
    cc: List[EmailStr]
    class Meta:
        model = EmailTemplate
        exclude = [*MUTATE_EXCLUDE_FIELDS, "created_by"]



class EmailTemplateListSchema(ModelSchema):
    class Meta:
        model = EmailTemplate
        fields = ("uid", "name", "personal","created_at")

class EmailTemplateAttachmentSchema(ModelSchema):
    url: Optional[str] = None
    class Meta:
        model = EmailTemplateAttachment
        fields = ("uid", "created_at")


class EmailTemplateDetailSchema(ModelSchema):
    sender: EmailStr
    placeholders: List[PlaceHolderType]
    bcc: List[EmailStr]
    cc: List[EmailStr]
    attachments: List[EmailTemplateAttachmentSchema]

    class Meta:
        model = EmailTemplate
        exclude= [*READ_EXCLUDE_FIELDS, "created_by"]


class MutateWorkFlowStageSchema(ModelSchema):
    phase: PlaceHolderType
    email_template: Optional[UUID]
    class Meta:
        model = WorkFlowStage
        exclude = [*MUTATE_EXCLUDE_FIELDS, "created_by"]

class WorkFlowStageSchema(ModelSchema):
    email_template: EmailTemplateListSchema
    can_be_deactivated:bool

    class Meta:
        model = WorkFlowStage
        exclude = [*READ_EXCLUDE_FIELDS, "created_by"]

class PhaseWorkFlowStageSchema(Schema):
    phase: List[str]
    stages: List[WorkFlowStageSchema]
