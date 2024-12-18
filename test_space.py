import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.jobs.tasks import job_performance_notification_task, job_application_notification_task, \
    job_sharing_notification_task

job_performance_notification_task()

job_application_notification_task()

job_sharing_notification_task()

