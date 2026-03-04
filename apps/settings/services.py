import dataclasses
import html
from typing import List, Optional

from accounts.models import Talent, BusinessUser
from django.template import Context
from django.utils.html import strip_tags
from settings.models import EmailTemplate

from helpers.email.utils import send_email, send_template_email
from monkeypatches.q_cluster import async_task


@dataclasses.dataclass
class PersonalEmailEngine:
    emails: List[str]
    has_placeholder: bool
    recruiter: BusinessUser  #UUID
    from_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    attachments: Optional[List[str]] = None
    attachment_urls: Optional[List[str]] = None

    def send(self):
        if self.has_placeholder is False:
            self.send_bulk_email()
            return
        attachments = [attachment.file.url for attachment in EmailTemplate.emailtemplateattachment_set.all()]
        for email in self.emails:
            talent = Talent.objects.filter(user__email=email).first()
            if not talent:
                continue
            async_task(self.send_individual_email,
                     from_email=self.from_email,
                       emails=[email],
                       subject=self.subject,
                       body=self.body,
                       recruiter=self.recruiter,
                       talent=talent,
                       template_attachments=attachments,
                       attachments=self.attachments
            )


    def send_bulk_email(self):
        # normal sender
        async_task(send_email, subject=self.subject, emails=self.emails, html_body=self.body,
                   attachments=self.attachments,
                   from_user=self.from_email, attachment_urls=self.attachment_urls)
        return

    @staticmethod
    def send_individual_email(from_email, emails, subject, body, recruiter: BusinessUser, talent: Talent, template_attachments: List[str]=None, attachments: list=None):
        converter = EmailTemplate.convert_placeholder_to_key
        context = {converter(placeholder): talent.placeholders_mapper(placeholder, recruiter) for placeholder in
                   EmailTemplate.placeholder}

        EmailTemplate.send_email(context=context, to=emails, sender=from_email)

        subject = EmailTemplate.convert_to_template(str(subject), is_html=True).render(Context(context))
        message = EmailTemplate.convert_to_template(str(body), is_html=True).render(Context(context))

        body = strip_tags(message)
        html_content = message
        data = dict(
            subject=html.unescape(subject),
            body=body,
            html_content=html_content,
            emails=emails,
            from_user=from_email
        )
        if attachments:
            data["attachments"] = attachments
        if template_attachments:
            data["attachment_urls"] = template_attachments

        send_template_email(**data)
        return





