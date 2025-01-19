from typing import List, Any

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from pydantic import EmailStr

from helpers.decorators import test_env_decorator
from helpers.loggers import Logger
from helpers.utils import is_valid_email


@test_env_decorator(None)
def send_email(subject:str, emails:List[EmailStr], html_body:str = None, plain_body:str=None):
    retries = 3
    for retry in range(retries):
        try:
            body = plain_body or strip_tags(html_body)
            email =EmailMultiAlternatives(
                    subject=subject,
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    bcc=emails,
                )
            if html_body:
                email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=False)
            return
        except Exception as e:
            Logger.error(dict(
                sender="Email Service",
                title="Email was not successfully sent",
                description=str(e)
            ), exc_info=True)

@test_env_decorator(None)
def send_template_email(subject:str, body:str, emails:List[EmailStr], from_user:str, attachment_urls:List[str]=None,
                        bcc:List[EmailStr]=None, cc:List[EmailStr]=None):
    html_content = render_html_email("email_template.html", dict(body=body))
    retries = 3

    if is_valid_email(from_user):
        user = from_user.split("@")[0].title()
        company = from_user.split("@")[1].split(".")[0].title()
        if company.lower() in ("gmail", "outlook", "hotmail", "yahoo"):
            from_user = user
        else:
            from_user = f"{user} from {company}"

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
            email.send(fail_silently=False)
            return
        except Exception as e:
            Logger.error(dict(
                sender="Email Service",
                title="Email Template was not successfully sent",
                description=str(e)
            ), exc_info=True)




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


