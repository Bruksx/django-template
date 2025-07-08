import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from services.job_posting.services import indeed

jobs = indeed.JobPost.objects.all()[:2]
for job in jobs:
    print(indeed.convert_job_object_to_job(job))

