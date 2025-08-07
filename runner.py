import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
# from django.db.models import Count, Avg, Sum, F, Subquery, Q, OuterRef, JSONField, Exists
# from jobs.models import TalentApplicationStageTimeline, Job, JobApplication, JobInvite
# from settings.models import WorkFlowStage
# from jobs.enums import PhaseType
#
#
# job = Job.objects.annotate(count=Count('jobpost__jobapplication')).order_by('-count').first()
# job_post = job.jobpost_set.annotate(count=Count('jobapplication')).order_by('-count').first()
#
# application:JobApplication = job_post.jobapplication_set.filter(stage__phase=PhaseType.REJECTED.value).first()
# business = job.created_by.business
# job_role_id = job.role_id
# stages = WorkFlowStage.objects.filter(created_by__business=business).order_by("phase_order", "order")
#
# job.workflow_stage_data()
#
# job_post.workflow_stage_data()
#
# JobApplication.objects.filter(id=99).update(stage=stages.filter(phase=PhaseType.NEW.value).first())
# # JobApplication.objects.filter(id=99).delete()
#
# application_count = job_post.jobapplication_set.count()
# query = JobApplication.objects.select_related("stage", "applicant", "applicant__user",
#                                                      "applicant__country").annotate(invited=Exists(Subquery(JobInvite.objects.filter(
#             job=OuterRef('job_post__job'), talent=OuterRef('applicant')
#         )))).filter(job_post__uid=job_post.uid, recruiter__business=business,
#                                              applicant__deleted_at__isnull=True)
# print(application_count)
# print()
# print(job_post.workflow_stage_data())
#
# print(job_post.workflow_stage_data())
#
# print(query)
# print(query.count())
# print(JobApplication.global_objects.filter(id=99).first().deleted_at)
#
# for ap in JobApplication.global_objects.filter(job_post=job_post):
#     ap.restore()
