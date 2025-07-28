import os
from random import randint

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from jobs.models import Job, BusinessModel

for job in Job.objects.iterator():
    job.business_models.set(BusinessModel.objects.all().order_by("?")[:randint(2, 5)])
    job.save()
print("updated jobs with recent business models")

