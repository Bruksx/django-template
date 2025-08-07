import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from jobs.models import JobPost
from jobs.queries import add_job_post_annotations

from jobs.models import JobApplication

# job = Job.objects.annotate(count=Count('jobpost__jobapplication')).order_by('-count').first()
# job_post = job.jobpost_set.annotate(count=Count('jobapplication')).order_by('-count').first()
#
# application:JobApplication = job_post.jobapplication_set.filter(stage__phase=PhaseType.REJECTED.value).first()
# business = job.created_by.business
# job_role_id = job.role_id
# stages = WorkFlowStage.objects.filter(created_by__business=business).order_by("phase_order", "order")
# recruiter = application.recruiter
# job.workflow_stage_data()
#
# job_post.workflow_stage_data()
#
# JobApplication.objects.get(id=99).update(stage=stages.filter(phase=PhaseType.HIRED.value).first())
# JobApplication.objects.filter(id=99).update(recruiter=None)
#
# application_count = job_post.jobapplication_set.count()
# query = JobApplication.objects.select_related("stage", "applicant", "applicant__user",
#                                                      "applicant__country").annotate(invited=Exists(Subquery(JobInvite.objects.filter(
#             job=OuterRef('job_post__job'), talent=OuterRef('applicant')
#         )))).filter(job_post__uid=job_post.uid, stage__created_by__business=business,
#                                              applicant__deleted_at__isnull=True)
# print(application_count)
# print()
# print(job_post.workflow_stage_data())
#
# print(job_post.workflow_stage_data())
#
# print(query.filter(id=99).first())
# print(query.count())
# print(JobApplication.global_objects.filter(id=99).first())

# for ap in JobApplication.global_objects.filter(job_post=job_post):
#     ap.restore()
# print([TimeToHireViaStages(**dt) for dt in (business.time_to_hire_via_stage())])

for ja in JobApplication.objects.iterator():
    jp = add_job_post_annotations(JobPost.objects.filter(id=ja.job_post_id), ja.applicant).first()
    if not jp:
        ja.update(match=0)
    else:
        print("computed_match_score", jp.computed_match_score)
        ja.update(match=int(jp.computed_match_score))
