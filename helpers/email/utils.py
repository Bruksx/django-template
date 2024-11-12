from typing import List
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.template.loader import render_to_string
from pydantic import EmailStr

from helpers.decorators import test_env_decorator
from helpers.loggers import Logger

@test_env_decorator(None)
def send_email(subject:str, emails:List[EmailStr], html_body:str = None, plain_body:str=None):
    retries = 3
    for retry in range(retries):
        try:
            body = plain_body or html_body
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


