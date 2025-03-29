from config import settings
from django.conf import settings
from django.db import transaction
from helpers.utils import upload_to_s3, upload_to_server
from ninja.errors import HttpError

from jobs.enums import PhaseType
from jobs.models import JobApplication, Answer
from jobs.schemas import ApplyToJobSchema
from notification.notifications import send_talents_job_matching_notification
from settings.models import WorkFlowStage


def get_talent_job_recommendations(talent, search="", use_filter=False, **kwargs):
    queryset = talent.job_post_matches()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        if not hasattr(talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = talent.jobfilter.get_queryset(queryset)

    return queryset.order_by("-created_at")

@transaction.atomic
def create_job_application(job_post, talent, data:ApplyToJobSchema):
    stage = (WorkFlowStage.objects.filter(phase=PhaseType.NEW.value, created_by__business=job_post.job.created_by.business)
             .order_by("order").first())
    application = JobApplication.objects.create(job_post=job_post, applicant=talent,
                                                recruiter=job_post.recruiter,
                                                stage=stage,
                                                available_for_schedule=data.available_for_schedule,
                                                match=talent.job_match_score(job_post))
    if job_post.job.min_match_score and application.match < job_post.job.min_match_score:
        rejected_stage = WorkFlowStage.objects.filter(
            phase=PhaseType.REJECTED.value,
            created_by__business=job_post.job.created_by.business
        ).order_by("order").first()
        application.update(stage=rejected_stage)

    if not data.answers:
        return
    for answer_data in data.answers:
        answer = Answer.objects.create(application=application,
                        question=answer_data.question, text=answer_data.text,
                        files=answer_data.files)
        if answer_data.options:
            answer.options.set(answer_data.options)
        answer.save()
    if application.stage and application.stage.phase != PhaseType.REJECTED.value and application.knockout():
        rejected_stage = WorkFlowStage.objects.filter(
            phase=PhaseType.REJECTED.value,
            created_by__business=job_post.job.created_by.business
        ).order_by("order").first()
        application.update(stage=rejected_stage)
    return

def upload_answer_files_service(files):
    if settings.USE_AWS_S3:
        return upload_to_s3(files, "answers")
    return upload_to_server(files, "answers")

def notify_business_on_matched_talents(job):
    posts = job.jobpost_set.all()
    for post in posts:
        talent_count = post.get_talents().count()
        send_talents_job_matching_notification(talent_count, post)

