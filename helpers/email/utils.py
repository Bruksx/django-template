import sys
from typing import List

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from pydantic import EmailStr

from helpers.loggers import Logger
from helpers.utils import is_valid_email


def batch_send(func, **kwargs):
    emails = kwargs.pop("emails", list())
    cc = kwargs.pop("cc", list())
    bcc = kwargs.pop("bcc", list())
    number_of_addresses = len(emails)
    number_of_cc = len(cc)
    number_of_bcc = len(bcc)
    batches = number_of_addresses // 40
    batches_cc = number_of_cc // 40
    batches_bcc = number_of_bcc // 40
    remainder = number_of_addresses % 40
    remainder_cc = number_of_cc % 40
    remainder_bcc = number_of_bcc % 40

    for batch in range(batches):
        if cc:
            kwargs["cc"] = cc[batch * 40: (batch + 1)* 40]
        if bcc:
            kwargs["bcc"] = bcc[batch * 40: (batch + 1) * 40]

        func(emails=emails[batch * 40: (batch + 1) * 40], **kwargs)
    if remainder:
        if cc:
            kwargs["cc"] = cc[-remainder_cc:]
        if bcc:
            kwargs["bcc"] = bcc[-remainder_bcc:]
        func(emails=emails[-remainder:], **kwargs)
    if batches_cc > batches:
        rem_batch = batches_cc - batches
        for batch in range(rem_batch):
            if cc:
                kwargs["cc"] = cc[batches+batch * 40: (batches+batch + 1) * 40]
            func(emails=[], **kwargs)
    if batches_bcc > batches:
        rem_batch = batches_bcc - batches
        for batch in range(rem_batch):
            if bcc:
                kwargs["bcc"] = bcc[batches+batch * 40: (batches+batch + 1) * 40]
            func(emails=[], **kwargs)




def send_actual_email(subject:str, emails:List[str], html_body:str = None, plain_body:str=None,
               attachments:list=None, from_user:str=None, attachment_urls:List[str]=None, retries=3):
    for retry in range(retries):
        try:
            body = plain_body or strip_tags(html_body)
            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL if not from_user else f"{from_user} <{settings.EMAIL_HOST_USER}>",
                bcc=emails,
            )
            if html_body:
                email.attach_alternative(html_body, "text/html")
            if attachments:
                for attachment in attachments:
                    email.attach(attachment.name, attachment.read(), attachment.content_type)
            if attachment_urls:
                for url in attachment_urls:
                    response = requests.get(url)
                    response.raise_for_status()
                    email.attach(f"{url.split('/')[-1]}", response.content, mimetype=response.headers['Content-Type'])
            email.send(fail_silently=False)
            return
        except Exception as e:
            print("error: ", e)
            Logger.error(dict(
                sender="Email Service",
                title="Email was not successfully sent",
                description=str(e)
            ), exc_info=True)


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

    batch_send(send_actual_email, subject=subject, emails=emails, html_body=html_body, plain_body=plain_body, attachments=attachments,
               attachment_urls=attachment_urls, from_user=from_user)



def send_actual_template_email(subject:str, body:str, emails:List[str], from_user:str, attachment_urls:List[str]=None,
                        bcc:List[str]=None, cc:List[str]=None, html_content:str=None, attachments:list=None, retries=3):
    for retry in range(retries):
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=f"{from_user} <{settings.EMAIL_HOST_USER}>",
                to=emails
            )
            if bcc:
                email.bcc = bcc
            if cc:
                email.cc = cc
            if attachment_urls:
                for url in attachment_urls:
                    response = requests.get(url)
                    response.raise_for_status()
                    email.attach(f"{url.split('/')[-1]}", response.content, mimetype=response.headers['Content-Type'])
            email.attach_alternative(html_content, "text/html")
            if attachments:
                for attachment in attachments:
                    email.attach(attachment.name, attachment.read(), attachment.content_type)
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            return
        except Exception as e:
            Logger.error(dict(
                sender="Email Service",
                title="Email Template was not successfully sent",
                description=str(e)
            ), exc_info=True)



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

    batch_send(send_actual_template_email, subject=subject, body=body, emails=emails, from_user=from_user, attachment_urls=attachment_urls,
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


