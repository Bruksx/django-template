from typing import List, Optional
from uuid import UUID

from ninja import Field, UploadedFile
from ninja import ModelSchema, Schema
from ninja.errors import HttpError
from pydantic import EmailStr, validate_email

from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS
from jobs.enums import PhaseType
from settings.enums import PlaceHolderType
from settings.models import EmailTemplate, EmailTemplateAttachment, WorkFlowStage


class CreateEmailTemplateSchema(ModelSchema):
    sender: EmailStr
    placeholders: str = Field(examples=PlaceHolderType.values(),
                              description="placeholders separated by comma without spacing")
    bcc: Optional[str] = Field(examples=["bob@examples.com"], description="emails separated by commas without spacing",
                               default=None)
    cc: Optional[str] = Field(examples=["bob@examples.com"], description="emails separated by commas without spacing",
                              default=None)
    class Meta:
        model = EmailTemplate
        exclude = [*MUTATE_EXCLUDE_FIELDS, "created_by", "uid"]

    @staticmethod
    def validate_placeholders(placeholders:str):
        placeholders = placeholders.split(",")
        if any(placeholder not in PlaceHolderType.values() for placeholder in placeholders):
            raise ValueError("Invalid placeholders")
        return placeholders

    @staticmethod
    def validate_email_string_list(emails:str):
        if not emails:
            return list()
        emails = emails.split(",")
        for email in emails:
            try:
                validate_email(email)
            except ValueError:
                raise ValueError(f"Invalid email address: {email}")
        return emails

    @classmethod
    def is_valid(cls, data:dict, instance=None, raise_exception=True):
        try:
            if "bcc" in data:
                data["bcc"] = cls.validate_email_string_list(data["bcc"])
            if "cc" in data:
                data["cc"] = cls.validate_email_string_list(data["cc"])
            if "placeholders" in data:
                data["placeholders"] = cls.validate_placeholders(data["placeholders"])
            if "subject" in data:
                EmailTemplate.convert_to_template(data["subject"], data.get("is_html", False))
            if "template" in data:
                EmailTemplate.convert_to_template(data["template"], data.get("is_html", False))

            if instance:
                placeholders = instance.placeholders if "placeholders" not in data else data["placeholders"]
                subject = instance.subject if "subject" not in data else data["subject"]
                template = instance.template if "template" not in data else data["template"]
            else:
                placeholders = data["placeholders"]
                subject = data["subject"]
                template = data["template"]
            EmailTemplate.validate_placeholder_usage(placeholders, subject, template,is_html=data.get("is_html", False))
            return True
        except Exception as e:
            if raise_exception is True:
                raise HttpError(400, e.args[0])
            return False


class UpdateEmailTemplateSchema(CreateEmailTemplateSchema):
    subject: Optional[str] = None
    template: Optional[str] = None
    personal: Optional[bool] = None
    delays : Optional[int] = None
    is_html: Optional[bool] = False




class AddAttachmentsToEmailTemplateSchema(Schema):
    attachments: List[UploadedFile]


class EmailTemplateListSchema(ModelSchema):
    in_use: bool
    can_be_deleted: Optional[bool] = None
    class Meta:
        model = EmailTemplate
        fields = ("uid", "name", "personal","created_at", "is_html")

    @staticmethod
    def resolve_can_be_deleted(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        business_user = request.context.get("business_user")
        if not business_user:
            return None
        return obj.can_be_deleted(business_user)


class EmailTemplateAttachmentSchema(ModelSchema):
    url: Optional[str] = Field(alias="file_url")
    name: Optional[str] = Field(alias="file_name")
    class Meta:
        model = EmailTemplateAttachment
        fields = ("uid", "created_at")

class MoveApplicationToStageFromStageSchema(Schema):
    previous_stage_uid: UUID
    next_stage_uid: UUID

class EmailTemplateDetailSchema(ModelSchema):
    sender: EmailStr
    placeholders: List[PlaceHolderType]
    bcc: List[EmailStr]
    cc: List[EmailStr]
    attachments: List[EmailTemplateAttachmentSchema]
    in_use: bool
    can_be_deleted: Optional[bool] = None

    @staticmethod
    def resolve_can_be_deleted(obj, context):
        request = context.get("request")
        if not request:
            return
        if not hasattr(request, "context"):
            return
        business_user = request.context.get("business_user")
        if not business_user:
            return None
        return obj.can_be_deleted(business_user)

    class Meta:
        model = EmailTemplate
        exclude= [*READ_EXCLUDE_FIELDS, "created_by"]


class MutateWorkFlowStageSchema(ModelSchema):
    phase: PhaseType
    email_template: Optional[UUID] = None
    class Meta:
        model = WorkFlowStage
        exclude = [*MUTATE_EXCLUDE_FIELDS, "created_by", "phase_order", "order", "uid"]

class WorkFlowStageSchema(ModelSchema):
    email_template: Optional[EmailTemplateListSchema] = None
    can_be_deactivated:bool
    applications: int

    class Meta:
        model = WorkFlowStage
        exclude = [*READ_EXCLUDE_FIELDS, "created_by"]

class PhaseWorkFlowStageSchema(Schema):
    phase: str
    stages: List[WorkFlowStageSchema]


class RearrangeWorkflowStageSchema(Schema):
    stage_uids: List[UUID]
    phase: PhaseType