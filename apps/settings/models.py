import json
import re
from datetime import datetime, timedelta
from typing import List

from core.models import BaseModel
from django.db import models
from django.template import Template, Context, TemplateSyntaxError
from django_q.models import Schedule
from jobs.enums import PhaseType

from helpers.email.utils import send_template_email
from monkeypatches.q_cluster import async_task


class EmailTemplate(BaseModel):
    name = models.CharField(max_length=255)
    sender = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    placeholders = models.JSONField(default=list)
    template = models.TextField()
    created_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.SET_NULL, null=True)
    personal = models.BooleanField(default=False)
    delays = models.PositiveSmallIntegerField(default=0)
    bcc = models.JSONField(default=list)
    cc = models.JSONField(default=list)

    regex = r"<([^>]*)>"

    def attachments(self):
        return self.emailtemplateattachment_set.all()

    @property
    def send_date(self)->datetime:
        return self.created_at + timedelta(days=self.delays)

    def send_email(self, context: dict, to:List[str]):
        keys = map(self.convert_key_to_placeholder, context.keys())
        self.validate_placeholders(placeholders=self.placeholders, members=list(keys))
        subject = self.convert_to_template(str(self.subject)).render(Context(context))
        message = self.convert_to_template(str(self.template)).render(Context(context))
        attachments = [attachment.file.url for attachment in self.emailtemplateattachment_set.all()]
        data = dict(
                    subject=subject,
                    body=message,
                    emails=to,
                    bcc=self.bcc,
                    cc=self.cc,
                    from_user=self.sender,
                    attachments=attachments
                )
        if self.delays == 0:
            async_task(send_template_email,
                       **data)
            return
        Schedule.objects.create(
            func='helpers.email.utils.send_template_email',
            schedule_type=Schedule.ONCE,
            next_run=self.send_date,
            kwargs=json.dumps(data)
        )

    @staticmethod
    def convert_placeholder_to_key(placeholder:str):
        return placeholder.replace(" ", "_").lower()

    @staticmethod
    def convert_key_to_placeholder(key:str):
        return key.replace("_", " ").upper()

    @staticmethod
    def validate_placeholders(members: List[str], placeholders:List[str], raise_exception=True):
        if any(member not in placeholders for member in members):
            if raise_exception is True:
                raise ValueError("Invalid placeholders")
            return False
        return True

    @classmethod
    def convert_to_template(cls, text: str)-> Template:
        match_func = lambda match: f"{{{{{cls.convert_placeholder_to_key(match.group(1))}}}}}"
        try:
            return Template(re.sub(cls.regex, match_func, text))
        except TemplateSyntaxError:
          raise ValueError("Invalid template syntax")

    @classmethod
    def validate_placeholder_usage(cls, placeholders:List[str], subject:str, template:str):
        subject_placeholders = re.findall(cls.regex, subject)
        if not cls.validate_placeholders(members=subject_placeholders, placeholders=placeholders,
                                         raise_exception=False):
            raise ValueError("Invalid placeholders in subject")
        template_placeholders = re.findall(cls.regex, template)
        if not cls.validate_placeholders(members=template_placeholders, placeholders=placeholders,
                                         raise_exception=False):
            raise ValueError("Invalid placeholders in template")
        return True


class EmailTemplateAttachment(BaseModel):
    email_template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    file = models.FileField(upload_to="email_attachments/")


    def file_url(self):
        if not self.file:
            return
        return self.file.url

class WorkFlowStage(BaseModel):
    phase = models.CharField(max_length=100, choices=PhaseType.choices())
    name = models.CharField(max_length=125)
    email_template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    def can_be_deactivated(self):
        return self.jobapplication_set.count() == 0




