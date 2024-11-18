from helpers.email.utils import render_text_email, send_email


def send_business_user_invitation_email(email:str, user_uid:str, user:str, business:str, lang="en"):
    context = {'code': user_uid, 'user': user, 'company': business}
    text = f"accounts/{lang}/business_user_invite.txt"
    text_content = render_text_email(text, context)
    send_email(subject=f"Invitation to {business}", emails=[email], plain_body=text_content)

def send_business_user_welcome_email(email:str, user:str, business:str, lang="en"):
    context = {'user': user, 'company': business}
    text = f"accounts/{lang}/business_user_welcome.txt"
    text_content = render_text_email(text, context)
    send_email(subject=f"Welcome to {business}", emails=[email], plain_body=text_content)