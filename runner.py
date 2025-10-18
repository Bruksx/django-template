import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Role
from jobs.models import Job
role = Role.objects.order_by("?").first()
Job.objects.filter(role__isnull=True).update(role=role)