from helpers.email.utils import render_text_email, send_email


def send_verification_code(email:str, code:str, user:str, company: None, lang="en"):
    context = {'code': code, 'user': user, 'company': company}
    text = f"accounts/{lang}/otp-email.txt"
    text_content = render_text_email(text, context)
    send_email(subject="One Time Password", emails=[email], plain_body=text_content)


