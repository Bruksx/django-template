import sys
from typing import List

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import loader
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from pydantic import EmailStr

from helpers.loggers import Logger
from helpers.utils import is_valid_email

BATCH_SIZE = 40


def _chunk_list(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]


def _batch_send(func, *, emails=None, cc=None, bcc=None, **kwargs):
    connection = get_connection()
    connection.open()

    emails = emails or []
    cc = cc or []
    bcc = bcc or []


    email_batches = list(_chunk_list(emails, BATCH_SIZE)) or []
    cc_batches = list(_chunk_list(cc, BATCH_SIZE)) or []
    bcc_batches = list(_chunk_list(bcc, BATCH_SIZE)) or []

    max_batches = max(len(email_batches), len(cc_batches), len(bcc_batches))
    try:
        for i in range(max_batches):
            _emails = email_batches[i] if i < len(email_batches) else []
            _cc = cc_batches[i] if i < len(cc_batches) else []
            _bcc = bcc_batches[i] if i < len(bcc_batches) else []
            if _cc:
                kwargs["cc"] = _cc
            if bcc:
                kwargs["bcc"] = _bcc

            func(
                connection=connection,
                emails=_emails,
                **kwargs
            )
    finally:
        connection.close()

def _send_email_core(
    connection,
    subject,
    body,
    from_email,
    to=None,
    cc=None,
    bcc=None,
    html_content=None,
    attachments=None,
    attachment_urls=None,
    retries=3,
):
    to = to or []
    cc = cc or []
    bcc = bcc or []

    for retry in range(retries):
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=from_email,
                to=to,
                cc=cc,
                bcc=bcc,
                connection=connection
            )

            if html_content:
                email.attach_alternative(html_content, "text/html")

            if attachments:
                for attachment in attachments:
                    email.attach(
                        attachment.name,
                        attachment.read(),
                        attachment.content_type
                    )

            if attachment_urls:
                for url in attachment_urls:
                    response = requests.get(url)
                    response.raise_for_status()

                    filename = url.split("/")[-1]
                    mimetype = response.headers.get("Content-Type")

                    email.attach(filename, response.content, mimetype)

            email.send(fail_silently=False)
            return

        except Exception as e:
            Logger.error(
                dict(
                    sender="Email Service",
                    title="Email was not successfully sent",
                    description=str(e),
                ),
                exc_info=True
            )

            if retry == retries - 1:
                raise

def _send_actual_email(
    connection,
    subject: str,
    emails: List[str],
    html_body: str = None,
    plain_body: str = None,
    attachments: list = None,
    from_user: str = None,
    attachment_urls: List[str] = None,
    retries=3,
):

    body = plain_body or strip_tags(html_body)

    from_email = (
        settings.DEFAULT_FROM_EMAIL
        if not from_user
        else f"{from_user} <{settings.EMAIL_HOST_USER}>"
    )

    _send_email_core(
        connection=connection,
        subject=subject,
        body=body,
        from_email=from_email,
        bcc=emails,
        html_content=html_body,
        attachments=attachments,
        attachment_urls=attachment_urls,
        retries=retries,
    )
def send_email(subject:str, emails:List[EmailStr], html_body:str = None, plain_body:str=None,
               attachments:list=None, from_user:str=None, attachment_urls:List[str]=None):
    if "test" in sys.argv:
        return
    correct_emails = list()
    for email in emails:
        try:
            if email.split("@")[1].split(".")[0].lower() not in ("example", "localhost", "test"):
                correct_emails.append(email)
        except:
            continue
    emails = correct_emails
    if not emails:
        return
    if from_user:
        if is_valid_email(from_user):
            user = from_user.split("@")[0].title()
            company = from_user.split("@")[1].split(".")[0].title()
            if company.lower() in ("gmail", "outlook", "hotmail", "yahoo"):
                from_user = user
            else:
                from_user = f"{user} from {company}"

    _batch_send(_send_actual_email, subject=subject, emails=emails, html_body=html_body, plain_body=plain_body,
                attachments=attachments, attachment_urls=attachment_urls, from_user=from_user)



def _send_actual_template_email(
    connection,
    subject: str,
    body: str,
    emails: List[str],
    from_user: str,
    attachment_urls: List[str] = None,
    bcc: List[str] = None,
    cc: List[str] = None,
    html_content: str = None,
    attachments: list = None,
    retries=3,
):

    from_email = f"{from_user} <{settings.EMAIL_HOST_USER}>"

    _send_email_core(
        connection=connection,
        subject=subject,
        body=body,
        from_email=from_email,
        to=emails,
        cc=cc,
        bcc=bcc,
        html_content=html_content,
        attachments=attachments,
        attachment_urls=attachment_urls,
        retries=retries,
    )

def send_template_email(subject:str, body:str, emails:List[str], from_user:str, attachment_urls:List[str]=None,
                        bcc:List[str]=None, cc:List[str]=None, html_content:str=None, attachments:list=None):
    if not bcc:
        bcc = []
    if not cc:
        cc = []
    html_content = render_html_email("email_template.html", dict(body=body, html_content=html_content))
    if "test" in sys.argv:
        return
    emails = [email for email in emails if
              email.split("@")[1].split(".")[0].lower() not in ("example", "localhost", "test")]
    bcc = [email for email in bcc if
              email.split("@")[1].split(".")[0].lower() not in ("example", "localhost", "test")]
    cc = [email for email in cc if
              email.split("@")[1].split(".")[0].lower() not in ("example", "localhost", "test")]
    if not emails and not bcc and not cc:
        return

    if is_valid_email(from_user):
        user = from_user.split("@")[0].title()
        company = from_user.split("@")[1].split(".")[0].title()
        if company.lower() in ("gmail", "outlook", "hotmail", "yahoo"):
            from_user = user
        else:
            from_user = f"{user} from {company}"

    _batch_send(_send_actual_template_email, subject=subject, body=body, emails=emails, from_user=from_user, attachment_urls=attachment_urls,
                bcc=bcc, cc=cc, html_content=html_content, attachments=attachments)






def render_text_email(file: str, context: dict):
    context["frontend_url"] = settings.FRONTEND_URL
    if not context.get("company"):
        context["company"] = settings.COMPANY_NAME
    return render_to_string(file, context)

def render_html_email(file: str, context: dict):
    context["frontend_url"] = settings.FRONTEND_URL
    if not context.get("company"):
        context["company"] = settings.COMPANY_NAME

    template = loader.get_template(file)
    return template.render(context)


