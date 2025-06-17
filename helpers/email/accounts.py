from helpers.email.utils import send_email, render_html_email
from helpers.utils import create_url_with_params


def send_business_user_invitation_email(email:str, user_uid:str, user:str, business:str, lang="en"):
    link = f"{{frontend_url}}/accounts/accept-invitation"
    link = create_url_with_params(link, {"code": user_uid, "company": business})
    context = {'code': user_uid, 'user': user, 'company': business, 'link': link}
    html_file = f"accounts/{lang}/business_user_invite.html"
    html_content = render_html_email(html_file, context)
    send_email(subject=f"Invitation to {business}", emails=[email], html_body=html_content)

def send_business_user_welcome_email(email:str, user:str, business:str, lang="en"):
    context = {'user': user, 'company': business}
    html_file = f"accounts/{lang}/business_user_welcome.html"
    html_content = render_html_email(html_file, context)
    send_email(subject=f"Welcome to {business}", emails=[email], html_body=html_content)