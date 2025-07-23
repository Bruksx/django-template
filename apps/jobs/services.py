from typing import List
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from jobs.enums import PhaseType
from jobs.models import JobApplication, Answer, RequiredAttribute, ScreeningQuestion, Job, JobPost
from jobs.schemas import ApplyToJobSchema, MutateRequiredAttributeSchema
from ninja.errors import HttpError
from notification.notifications import send_talents_job_matching_notification
from settings.models import WorkFlowStage

from jobs.enums import JobStatusType
from config import settings
from helpers.utils import sort_params_function
from helpers.utils import upload_to_s3, upload_to_server
from monkeypatches.q_cluster import async_task


def get_talent_job_recommendations(talent, business=None, search=""):
    queryset = talent.job_post_matches(by_talent_country=False, business=business)
    if search:
        queryset = queryset.filter(job__role__name__icontains=search)
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


def set_job_required_attributes(data:dict, job):
    MutateRequiredAttributeSchema.validate_required_attribute(data, job)
    required_attributes, _ = RequiredAttribute.objects.get_or_create(job=job)
    required_attributes.skills.set(data.pop("skills"))
    required_attributes.business_models.set(data.pop("business_models"))
    required_attributes.update(**data)
    async_task(notify_business_on_matched_talents, job=job)
    return required_attributes

def order_job_posts(queryset, sorts:List[str]=None, *extra_sort_params:List[str])->QuerySet:
    """
    sort job posts

    Args:
        queryset: job posts queryset
        sorts: list of sort parameters based on API query
        *extra_sort_params: extra sort parameters based on model fields
    """
    mapper = {"date-posted": "date_posted", "job-level": "job__job_level"}
    sort_values = []
    if sorts:
        sort_values = sort_params_function(sorts, mapper)
    if not sort_values:
        sort_values = ["-created_at", *extra_sort_params]
    return queryset.order_by(*sort_values)

def get_screening_questions_service(request, job_uid:UUID):
    if not Job.objects.filter(uid=job_uid, created_by__business=request.user.businessuser.business).exists():
        raise HttpError(404, "This job does not exist")
    screening_questions = ScreeningQuestion.objects.filter(job__uid=job_uid)
    return screening_questions.filter(job__created_by__business=request.user.businessuser.business)


def update_job_post_service(job_post, business_user, data=None, status=None):
    new_job = None
    if not data:
        data = dict()
    if status:
        data["status"] = status
        if status == JobStatusType.POSTED.value:
            data["posted_by"] = business_user
            data["date_posted"] = timezone.now()
        if status == JobStatusType.DRAFT.value and job_post.status != JobStatusType.DRAFT.value:
            # you're trying to prevent editing job posts with applications
            new_job = job_post.copy()


    if new_job:
        job_post.update(status=JobStatusType.CLOSED.value)
        new_job.update(**data)
        return new_job
    return job_post.update(**data)

def update_bulk__job_posts_service(business_user, job_posts_id, action):
    for job_post in JobPost.objects.filter(uid__in=job_posts_id, job__created_by__business=business_user.business).iterator():
        update_job_post_service(job_post, business_user, status=action.value)
