import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from jobs.models import JobPost
from jobs.queries import add_job_post_annotations
from notification.models import Notification
from notification.enums import NotificationType, EntityType, NotificationGroup
from accounts.models import Business

from accounts.enums import BusinessUserRoleType

from jobs.models import JobApplication

# for ja in JobApplication.objects.iterator():
#     jp = add_job_post_annotations(JobPost.objects.filter(id=ja.job_post_id), ja.applicant).first()
#     if not jp:
#         ja.update(match=0)
#     else:
#         print("computed_match_score", jp.computed_match_score)
#         ja.update(match=int(jp.computed_match_score))
#
#
# Notification.objects.all().hard_delete()
job_post = JobPost.objects.first()
business = Business.objects.first()
notification = Notification.objects.create(
        # title="Job Performance Weekly Update",
        # description=f"Weekly Update:",
        # notification_type=NotificationType.PERFORMANCE.value,
        # entity=EntityType.JOB_POST.value,
        # entity_uid=job_post.uid,
        # entity_str=job_post.job.get_title,
        recipient_groups=[NotificationGroup.TALENTS.value, NotificationGroup.BUSINESS_USERS.value],
        # role=BusinessUserRoleType.OWNER.value,
        business=business
    )



print(notification.get_recipients())
print(notification.get_recipients().count())