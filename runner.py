import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from helpers.email.utils import send_template_email

send_template_email("Hello", "Hello bro", ["biwiyiy557@foxroids.com",
                                           "ohaegbulouis@gmail.com"], "1840gtc",
                    )