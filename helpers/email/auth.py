from config import settings
from helpers.email.utils import render_text_email, send_email


def send_verification_code(email:str, code:str, user:str, company=None, lang="en"):
    context = {'code': code, 'user': user, 'company': company}
    html_file = f"accounts/{lang}/otp-email.html"
    html_content = render_text_email(html_file, context)
    send_email(subject="One Time Password", emails=[email], html_body=html_content)



def send_email_verification_code(email:str, token:str, fullname:str, company=None, lang="en"):
    verify_link = f"{settings.FRONTEND_URL}onboarding/organization/verified-email?token={token}"
    context = {'link': verify_link, 'user': fullname, 'company': company}
    html_file = f"accounts/{lang}/verify-email.html"
    html_content = render_text_email(html_file, context)
    send_email(subject="Email Verification", emails=[email], html_body=html_content)



