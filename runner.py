import os

import django
from django.db.models import F, Case, When, FloatField, Avg
from django.db.models.functions import Extract, Coalesce, Now


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Business

# for ja in JobApplication.objects.iterator():
#     jp = add_job_post_annotations(JobPost.objects.filter(id=ja.job_post_id), ja.applicant).first()
#     if not jp:
#         ja.update(match=0)
#     else:
#         print("computed_match_score", jp.computed_match_score)
#         ja.update(match=int(jp.computed_match_score))
from settings.models import WorkFlowStage
from jobs.enums import PhaseType


from jobs.models import TalentApplicationStageTimeline
for business in Business.objects.iterator():
    print(business.time_to_hire_via_stage())
    print(business.time_to_hire())
    print("\n\n")
for t in TalentApplicationStageTimeline.objects.order_by("?")[:2]:
    t.update(exit_date=None)

t = TalentApplicationStageTimeline.objects.annotate(
    days=Extract(
    Coalesce(F('exit_date'), Now()) - F('created_at')
    , 'epoch')).annotate(time_spent=Case(
    When(days__isnull=True, then=0),
    default=F('days')/86400.0,
output_field=FloatField())).values("stage__phase").annotate(days_to_hire=Avg("time_spent"))

print(t.values("stage__phase", "days_to_hire").order_by("stage__phase_order", "stage__order"))


w = WorkFlowStage.objects.order_by("phase_order", "order").exclude(phase__in=(PhaseType.HIRED.value, PhaseType.REJECTED.value)).annotate(
    days=Extract(
    Coalesce(F('talentapplicationstagetimeline__exit_date'), Now()) - F('talentapplicationstagetimeline__created_at')
    , 'epoch')).annotate(time_spent=Case(
    When(days__isnull=True, then=0),
    default=F('days')/86400.0,
output_field=FloatField())).values("phase").annotate(days_to_hire=Avg("time_spent"))

print(w.values("phase", "days_to_hire"))
