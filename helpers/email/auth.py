from helpers.email.utils import render_text_email, send_email


def send_verification_code(email:str, code:str, user:str, company=None, lang="en"):
    context = {'code': code, 'user': user, 'company': company}
    html_file = f"accounts/{lang}/otp-email.html"
    html_content = render_text_email(html_file, context)
    send_email(subject="One Time Password", emails=[email], html_body=html_content)


