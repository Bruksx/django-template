import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from helpers.email.accounts import send_business_user_invitation_email


send_business_user_invitation_email(
    email="ohaegbulouis@gmail.com",
    user_uid="345678909876543",
    user="Ohaegbu Louis",
    business="Heckerbella"
)