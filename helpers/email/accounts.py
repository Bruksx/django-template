from django.conf import settings

from helpers.email.utils import send_email, render_html_email
from helpers.utils import create_url_with_params


def send_business_user_invitation_email(email:str, token:str, user:str, business:str, lang="en"):
    link = f"{settings.FRONTEND_URL}onboarding/organization/welcome"
    link = create_url_with_params(link, {"code": token, "company": business})
    context = {'code': token, 'user': user, 'company': business, 'link': link}
    html_file = f"accounts/{lang}/business_user_invite.html"
    html_content = render_html_email(html_file, context)
    send_email(subject=f"Invitation to {business}", emails=[email], html_body=html_content)

def send_business_user_welcome_email(email:str, user:str, business:str, lang="en"):
    context = {'user': user, 'company': business}
    html_file = f"accounts/{lang}/business_user_welcome.html"
    html_content = render_html_email(html_file, context)
    send_email(subject=f"Welcome to {business}", emails=[email], html_body=html_content)


def send_customer_case_email(sender,reason: str, subject:str, description, lang="en"):
    context = {'sender': sender.fullname, 'email': sender.email, 'account_type': sender.type,
               'reason': reason, 'description': description}
    html_file = f"accounts/{lang}/customer_case_email.html"
    html_content = render_html_email(html_file, context)
    send_email(subject=subject, emails=["contact@1840andco.com"], html_body=html_content)
