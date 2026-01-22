import dataclasses
import html
import json
from typing import List, Optional

from accounts.models import Talent, BusinessUser
from django.template import Context
from django.utils.html import strip_tags
from ninja.errors import HttpError
from settings.models import EmailTemplate

from helpers.email.utils import send_email, send_template_email
from helpers.loggers import LogSchema, Logger
from monkeypatches.q_cluster import async_task


@dataclasses.dataclass
class PersonalEmailEngine:
    emails: List[str]
    recruiter: BusinessUser  #UUID
    from_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    attachments: Optional[List[str]] = None
    email_template: Optional[EmailTemplate] = None #UUID



    def initialize(self):
        self.__validate__()
        if self.email_template:
            if not self.subject:
                self.subject = self.email_template.subject
            if not self.body:
                self.body = self.email_template.template
            if not self.from_email:
                self.from_email = self.email_template.sender


    # can be attached to the schema
    def __validate__(self):
        if not self.emails:
            raise HttpError(400, "Emails are required")
        if not self.email_template and not (self.from_email or self.subject or self.body or self.attachments or self.placeholders):
            raise HttpError(400, "Email template or from email, subject, body, attachments, placeholders are required")


    def send(self):
        self.initialize()
        if not self.email_template:
            self.send_bulk_email()
            return
        attachments = [attachment.file.url for attachment in self.email_template.emailtemplateattachment_set.all()]
        for email in self.emails:
            talent = Talent.objects.filter(user__email=email).first()
            if not talent:
                continue
            async_task(self.send_individual_email,
                     from_email=self.from_email,
                       emails=[email],
                       subject=self.subject,
                       body=self.body,
                       email_template=self.email_template,
                       recruiter=self.recruiter,
                       talent=talent,
                       template_attachments=attachments,
                       attachments=self.attachments
            )


    def send_bulk_email(self):
        # normal sender
        async_task(send_email, subject=self.subject, emails=self.emails, html_body=self.body,
                   attachments=self.attachments,
                   from_user=self.from_email)
        return

    @staticmethod
    def send_individual_email(from_email, emails, subject, body, email_template, recruiter: BusinessUser, talent: Talent, template_attachments: List[str]=None, attachments: list=None):
        converter = email_template.convert_placeholder_to_key
        context = {converter(placeholder): talent.placeholders_mapper(placeholder, recruiter) for placeholder in
                   email_template.placeholder}
        keys = map(email_template.convert_key_to_placeholder, context.keys())

        email_template.send_email(context=context, to=emails, sender=from_email)

        is_valid_placeholders = email_template.validate_placeholders(placeholders=email_template.placeholders,
                                                                          members=list(keys),
                                                                          raise_exception=False)
        if not is_valid_placeholders:
            Logger.error(LogSchema(
                sender="Personal Email Template Model",
                title="Unable to send template email due to invalid placeholders",
                description=json.dumps(dict(
                    template_uid=str(email_template.uid),
                    placeholders=email_template.placeholders,
                    context=context,
                ))).__dict__)
            return

        subject = email_template.convert_to_template(str(subject), is_html=True).render(Context(context))
        message = email_template.convert_to_template(str(body), is_html=True).render(Context(context))

        body = strip_tags(message)
        html_content = message
        data = dict(
            subject=html.unescape(subject),
            body=body,
            html_content=html_content,
            emails=emails,
            bcc=email_template.bcc,
            cc=email_template.cc,
            from_user=from_email
        )
        if attachments:
            data["attachments"] = attachments
        if template_attachments:
            data["attachment_urls"] = template_attachments

        send_template_email(**data)
        return





