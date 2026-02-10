import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.tasks import send_weekly_report_of_candidates

send_weekly_report_of_candidates()

