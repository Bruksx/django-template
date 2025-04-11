import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from services.job_posting.linkedIn import LinkedInJobPostingService
from services.job_posting.services.linkedin import job_post_to_job_schema
from services.job_posting.enums.linkedIn import OperationTypeEnum

from jobs.models import JobPost
jobs = JobPost.objects.all()[:2]
jobs_obj = map(job_post_to_job_schema, jobs)

job_poster = LinkedInJobPostingService().call_endpoint(jobs, OperationTypeEnum.CREATE)

