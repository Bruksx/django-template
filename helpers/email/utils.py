from typing import List
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
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

