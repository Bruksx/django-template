import html
import json
import re
from datetime import datetime, timedelta
from typing import List

from accounts.enums import BusinessUserRoleType
from core.models import BaseModel
from django.db import models
from django.db.models import Q, Avg
from django.template import Context, TemplateSyntaxError
from django.utils.html import strip_tags
from django_q.models import Schedule
from jobs.enums import PhaseType
from settings.patch import CustomHTMLTemplate as Template

from helpers.email.utils import send_template_email
from helpers.loggers import Logger, LogSchema
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
    is_html = models.BooleanField(default=False)

    regex = r"<([^>]*)>" # this regex finds <placeholders>
    html_regex = r"\{\{([^}]*)\}\}" # this regex finds {{placeholders}}

    def attachments(self):
        return self.emailtemplateattachment_set.all()

    @property
    def send_date(self)->datetime:
        return self.created_at + timedelta(days=self.delays)

    def send_email(self, context: dict, to:List[str], sender:str):
        # we are retrieving the placeholders from the keys in the context
        keys = map(self.convert_key_to_placeholder, context.keys())

        # we want to ensure that the key is valid
        is_valid_placeholders = self.validate_placeholders(placeholders=self.placeholders, members=list(keys), raise_exception=False)
        if not is_valid_placeholders:
            Logger.error(LogSchema(
                sender="Email Template Model",
                title="Unable to send template email due to invalid placeholders",
                description=json.dumps(dict(
                    template_uid=str(self.uid),
                    placeholders=self.placeholders,
                    context=context,
                ))).__dict__)
            return
        subject = self.convert_to_template(str(self.subject),is_html=self.is_html).render(Context(context))
        message = self.convert_to_template(str(self.template),is_html=self.is_html).render(Context(context))
        attachments = [attachment.file.url for attachment in self.emailtemplateattachment_set.all()]
        if self.is_html is True:
            body = strip_tags(message)
            html_content = message
        else:
            body = message
            html_content = None
        data = dict(
                    subject=html.unescape(subject),
                    body=body,
                    html_content=html_content,
                    emails=to,
                    bcc=self.bcc,
                    cc=self.cc,
                    from_user=sender,
                    attachment_urls=attachments
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
        return key.replace("_", " ").title()

    @staticmethod
    def validate_placeholders(members: List[str], placeholders:List[str], raise_exception=True):
        if any(member not in placeholders for member in members):
            if raise_exception is True:
                raise ValueError("Invalid placeholders")
            return False
        return True

    @classmethod
    def convert_to_template(cls, text: str, is_html: bool = False)-> Template:
        regex = cls.html_regex if is_html is True else cls.regex
        match_func = lambda match: f"{{{{{cls.convert_placeholder_to_key(match.group(1))}}}}}"
        try:
            return Template(re.sub(regex, match_func, text))
        except TemplateSyntaxError:
          raise ValueError("Invalid template syntax")

    @classmethod
    def validate_placeholder_usage(cls, placeholders:List[str], subject:str, template:str, is_html:bool = False):
        regex = cls.html_regex if is_html is True else cls.regex
        subject_placeholders = re.findall(regex, subject)
        if not cls.validate_placeholders(members=subject_placeholders, placeholders=placeholders,
                                         raise_exception=False):
            raise ValueError("Invalid placeholders in subject")
        template_placeholders = re.findall(regex, template)
        if not cls.validate_placeholders(members=template_placeholders, placeholders=placeholders,
                                         raise_exception=False):
            raise ValueError("Invalid placeholders in template")
        return True

    def in_use(self):
        return not self.personal and self.workflowstage_set.exists()

    def can_be_deleted(self, business_user):
        if self.in_use():
            return False
        return self.created_by == business_user or business_user.role in [BusinessUserRoleType.ADMIN.value, BusinessUserRoleType.OWNER.value]



class EmailTemplateAttachment(BaseModel):
    email_template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    file = models.FileField(upload_to="email_attachments/")


    def file_url(self):
        if not self.file:
            return
        return self.file.url

    def file_name(self):
        if not self.file:
            return
        return self.file.name.split("/")[-1]

class WorkFlowStage(BaseModel):
    phase = models.CharField(max_length=100, choices=PhaseType.choices())
    name = models.CharField(max_length=125)
    email_template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey("accounts.BusinessUser", on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    phase_order = models.PositiveSmallIntegerField(default=0)
    order = models.PositiveSmallIntegerField(default=0)


    def applicants(self):
        return self.jobapplication_set

    def applications(self):
        return self.jobapplication_set.count()

    def average_timeline_by_talent(self):
        from jobs.models import TalentApplicationStageTimeline
        return TalentApplicationStageTimeline.add_time_spent_annotation(self.talentapplicationstagetimeline_set).aggregate(
            avg_timeline=Avg("time_spent")/86400.0
        )["avg_timeline"] or 0


    def can_be_deactivated(self):
        return self.applicants().count() == 0 and self.phase not in [PhaseType.NEW.value, PhaseType.REJECTED.value, PhaseType.HIRED.value]

    def previous_stages(self):
        """
        stages before this stage
        """
        return WorkFlowStage.objects.filter(
            created_by__business=self.created_by.business,
            phase_order__lte=self.phase_order
        ).filter(Q(order__lt=self.order, phase_order=self.phase_order) |
                 ~Q(phase_order=self.phase_order))

    def previous_stages_after_stage(self, stage):
        """
        stages before this stage then stopping at the
        stage passed to this function
        """
        if not self.is_after(stage):
            return WorkFlowStage.objects.none()

        return self.previous_stages().filter(
            phase_order__gte=stage.phase_order
        ).exclude(
            phase_order=stage.phase_order, order__lt=stage.order
        )

    def next_stages(self):
        """
        stages after this stage
        """
        return WorkFlowStage.objects.filter(
            created_by__business=self.created_by.business,
            phase_order__gte=self.phase_order
        ).filter(Q(order__gt=self.order, phase_order=self.phase_order) |
                 ~Q(phase_order=self.phase_order))

    def next_stages_before_stage(self, stage):
        """
            stages after this stage but stopping at the
            stage passed to this function
        """
        if self.is_behind(stage):
            return WorkFlowStage.objects.none()

        return self.next_stages().filter(
            phase_order__lte=stage.phase_order
        ).exclude(
            phase_order=stage.phase_order, order__gt=stage.order
        )

    def is_behind(self, stage):
        return (self.phase_order < stage.phase_order or
                (self.phase_order == stage.phase_order and self.order < stage.order))

    def is_after(self, stage):
        return (self.phase_order > stage.phase_order or
                (self.phase_order == stage.phase_order and self.order > stage.order))







