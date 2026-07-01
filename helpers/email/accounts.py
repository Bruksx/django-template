from typing import List

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


def send_incomplete_profile_reminder_email(emails: List[str], name: str=None, lang='en'):
    context = {
        "link": f"{settings.FRONTEND_URL}talent/profile",
        "name": name
    }
    html_file = f"accounts/{lang}/incomplete_profile_reminder.html"
    html_file = render_html_email(html_file, context)
    send_email(subject="Incomplete Profile Reminder", emails=emails, html_body=html_file)


def send_admin_invite_email(email:str, token:str, user:str, lang="en"):
    context = {
        "link": f"{settings.FRONTEND_URL}auth/admin-invite?code={token}",
        "user": user
    }
    html_file = f"accounts/{lang}/admin_invite.html"
    html_content = render_html_email(html_file, context)
    send_email(subject="Admin Invitation", emails=[email], html_body=html_content)

def send_first_talent_invitation_email(emails: List[str], lang="en"):
    context = {
        "link": f"{settings.FRONTEND_URL}onboarding/talent/registration",
    }
    html_file = f"accounts/{lang}/invite_talent_1.html"
    html_content = render_html_email(html_file, context)
    send_email(subject="You're invited to join 1840 Global Talent Cloud", emails=emails, html_body=html_content)

def send_second_talent_invitation_email(emails: List[str], lang="en"):
    context = {
        "link": f"{settings.FRONTEND_URL}onboarding/talent/registration",
    }
    html_file = f"accounts/{lang}/invite_talent_2.html"
    html_content = render_html_email(html_file, context)
    send_email(subject="Your invitation is still open", emails=emails, html_body=html_content)

def send_third_talent_invitation_email(emails: List[str], lang="en"):
    context = {
        "link": f"{settings.FRONTEND_URL}onboarding/talent/registration",
    }
    html_file = f"accounts/{lang}/invite_talent_3.html"
    html_content = render_html_email(html_file, context)
    send_email(subject="Final Reminder to join 1840 Global Talent Cloud", emails=emails, html_body=html_content)

def send_talent_account_activation_email(email:str, fullname:str, status:str, lang="en"):
    context = {
        "fullname": fullname,
        "status": status,
        "link": f"{settings.FRONTEND_URL}auth/login"
    }
    html_file = f"accounts/{lang}/activate_talent_account.html"
    html_content = render_html_email(html_file, context)
    send_email(subject="Your Account Has Been Deactivated", emails=[email], html_body=html_content)