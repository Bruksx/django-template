from typing import List, Optional
from uuid import UUID

from ninja import Field
from ninja import ModelSchema, Schema
from ninja.errors import HttpError
from pydantic import EmailStr, validate_email

from core.schemas import MUTATE_EXCLUDE_FIELDS, READ_EXCLUDE_FIELDS
from jobs.enums import PhaseType
from settings.enums import PlaceHolderType
from settings.models import EmailTemplate, EmailTemplateAttachment, WorkFlowStage


class MutateEmailTemplateSchema(ModelSchema):
    sender: EmailStr
    placeholders: str = Field(examples=PlaceHolderType.values(),
                              description="placeholders separated by comma without spacing")
    bcc: str = Field(examples=["bob@examples.com"], description="emails separated by commas without spacing")
    cc: str = Field(examples=["bob@examples.com"], description="emails separated by commas without spacing")
    class Meta:
        model = EmailTemplate
        exclude = [*MUTATE_EXCLUDE_FIELDS, "created_by"]

    @staticmethod
    def validate_placeholders(placeholders:str):
        placeholders = placeholders.split(",")
        if any(placeholder not in PlaceHolderType.values() for placeholder in placeholders):
            raise ValueError("Invalid placeholders")
        return placeholders

    @staticmethod
    def validate_email_string_list(emails:str):
        emails = emails.split(",")
        for email in emails:
            try:
                validate_email(email)
            except ValueError:
                raise ValueError(f"Invalid email address: {email}")
        return emails

    @staticmethod
    def is_valid(data:dict, instance=None, raise_exception=True):
        try:
            if "bcc" in data:
                data["bcc"] = MutateEmailTemplateSchema.validate_email_string_list(data["bcc"])
            if "cc" in data:
                data["cc"] = MutateEmailTemplateSchema.validate_email_string_list(data["cc"])
            if "placeholders" in data:
                data["placeholders"] = MutateEmailTemplateSchema.validate_placeholders(data["placeholders"])
            if "subject" in data:
                EmailTemplate.convert_to_template(data["subject"])
            if "template" in data:
                EmailTemplate.convert_to_template(data["template"])

            if instance:
                placeholders = instance.placeholders if "placeholders" not in data else data["placeholders"]
                subject = instance.subject if "subject" not in data else data["subject"]
                template = instance.template if "template" not in data else data["template"]
            else:
                placeholders = data["placeholders"]
                subject = data["subject"]
                template = data["template"]
            EmailTemplate.validate_placeholder_usage(placeholders, subject, template)
            return True
        except Exception as e:
            if raise_exception is True:
                raise HttpError(400, e.args[0])
            return False








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
    phase: PhaseType
    email_template: Optional[UUID] = None
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
    phase: str
    stages: List[WorkFlowStageSchema]
