import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from jobs.models import JobPost
from jobs.queries import add_job_post_annotations
from notification.models import Notification

from accounts.enums import BusinessUserRoleType

from jobs.models import JobApplication

for ja in JobApplication.objects.iterator():
    jp = add_job_post_annotations(JobPost.objects.filter(id=ja.job_post_id), ja.applicant).first()
    if not jp:
        ja.update(match=0)
    else:
        print("computed_match_score", jp.computed_match_score)
        ja.update(match=int(jp.computed_match_score))


Notification.objects.all().hard_delete()
