from config import settings
from helpers.email.utils import render_text_email, send_email


def send_verification_code(email:str, code:str, user:str, company=None, lang="en"):
    context = {'code': code, 'user': user, 'company': company}
    html_file = f"accounts/{lang}/otp-email.html"
    html_content = render_text_email(html_file, context)
    send_email(subject="One Time Password", emails=[email], html_body=html_content)


def send_admin_created_account_email(email: str, name: str, password: str, account_type: str, business_name: str = None, lang="en"):
    """
    Send email to users created by admin with their login credentials
    """
    context = {
        'email': email,
        'name': name,
        'password': password,
        'account_type': account_type,
        'business_name': business_name
    }
    html_file = f"accounts/{lang}/admin_created_account.html"
    html_content = render_text_email(html_file, context)
    send_email(
        subject="Welcome to 1840 Global Talent Cloud - Your Account is Ready",
        emails=[email],
        html_body=html_content
    )



def send_email_verification_code(email:str, token:str, fullname:str, company=None, lang="en"):
    verify_link = f"{settings.FRONTEND_URL}onboarding/organization/verified-email?token={token}"
    context = {'link': verify_link, 'user': fullname, 'company': company}
    html_file = f"accounts/{lang}/verify-email.html"
    html_content = render_text_email(html_file, context)
    send_email(subject="Email Verification", emails=[email], html_body=html_content)



