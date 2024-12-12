from typing import List
from uuid import UUID

from config.permissions import IsTalentUser, IsBusinessUser
from django.db import transaction
from monkeypatches.q_cluster import async_task
from ninja import Router, PatchDict, Form
from ninja.errors import HttpError
from ninja.responses import Response
from ninja_extra.pagination import PageNumberPaginationExtra, paginate
from ninja_extra.schemas import PaginatedResponseSchema
from ninja_jwt.authentication import JWTAuth

from accounts.models import Talent
from jobs import tasks
from jobs.enums import JobStatusType, PhaseType
from jobs.models import JobFilter, JobApplication, JobPost, JobApplicationWithdrawal, SavedJob, Answer, AnswerAttachment
from jobs.schemas import TalentJobPostListSchema, TalentJobFilterSchema, MutateTalentJobFilterSchema, \
    TalentJobApplicationWithdrawalSchema, ShareJobPostViaEmailSchema, ShareJobPostViaChatSchema, \
    TalentJobPostSchema, MutateAnswerSchema
from jobs.services import get_talent_job_recommendations, create_job_application
from notification import notifications
from settings.models import WorkFlowStage

router = Router()

@router.get("talent/job-recommendations", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def logged_in_talent_job_recommendations(request, search="", use_filter=False, **kwargs):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = {"talent": talent}
    return get_talent_job_recommendations(talent, search, use_filter, **kwargs)

@router.get("talents/{talent_uid}/job-recommendations", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_job_recommendations(request, talent_uid:UUID, search="", use_filter=False, **kwargs):
    IsBusinessUser.check(request)
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "Talent not found")
    request.context = {"talent": talent}
    return get_talent_job_recommendations(talent, search, use_filter, **kwargs)

@router.get("talent/saved-jobs", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_saved_jobs(request, search="", use_filter=False, **kwargs):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = {"talent": talent}
    queryset = talent.saved_jobs()
    if search:
        if not hasattr(talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        queryset = talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-savedjob__created_at")

@router.get("talent/job-posts", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def job_posts_by_talent_country(request, search="", use_filter=False, **kwargs):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = {"talent": talent}
    queryset = JobPost.objects.filter(country=talent.country, status=JobStatusType.POSTED.value)
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        if not hasattr(talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-created_at")

@router.get("talent/applied-jobs", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_applied_jobs(request, search="", use_filter=False, **kwargs):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = {"talent": talent}
    queryset = talent.applied_jobs()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        if not hasattr(talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-jobapplication__created_at")


@router.patch("talent/job-filter", auth=JWTAuth(), tags=["Talent Jobs"], response=TalentJobFilterSchema)
def update_talent_job_filter(request, data: PatchDict[MutateTalentJobFilterSchema]):
    IsTalentUser.check(request)
    talent = request.user.talent
    if "location_type" in data:
        data["location_type"] = data["location_type"].value
    if not hasattr(talent, "jobfilter"):
        JobFilter.objects.create(talent=talent, **data)
    else:
        talent.jobfilter.update(**data)
    talent.refresh_from_db()
    return talent.jobfilter

@router.get("talent/job-filter", auth=JWTAuth(), tags=["Talent Jobs"], response=TalentJobFilterSchema)
def get_talent_job_filter(request):
    IsTalentUser.check(request)
    talent = request.user.talent
    if not hasattr(talent, "jobfilter"):
        raise HttpError(400, "You have not set a job filter yet")
    return talent.jobfilter


@router.post("talent/job-posts/{job_post_id}/apply", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
@transaction.atomic
def apply_to_job_post(request, job_post_id:UUID, data:List[MutateAnswerSchema]):
    IsTalentUser.check(request)
    talent = request.user.talent
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    if job_post.status != JobStatusType.POSTED.value:
        raise HttpError(400, "Job post is no longer available")
    if JobApplication.objects.filter(job_post=job_post, applicant=talent).exists():
        raise HttpError(400, "Already applied")
    async_task(
        create_job_application, job_post=job_post, talent=talent, data=data
    )
    return Response(status=200, data={"message": "Applied successfully"})


@router.post("talent/job-posts/{job_post_id}", auth=JWTAuth(),
             description="this will notify the business connected to the job post if there is a match",
             response=TalentJobPostSchema, tags=["Talent Jobs"])
def view_job_post(request, job_post_id:UUID):
    IsTalentUser.check(request)
    talent = request.user.talent
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    notifications.send_talent_job_matching_notification(talent, job_post)
    return job_post


@router.post("talent/job-posts/applications/{application_id}/withdraw", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
def withdraw_job_applications(request, application_id:UUID, data: TalentJobApplicationWithdrawalSchema):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    application = JobApplication.objects.filter(uid=application_id).first()
    if not application:
        raise HttpError(404, "Application not found")
    if application.stage:
        raise HttpError(400, "You cannot withdraw this application at this time")
    feedback_type = JobApplicationWithdrawal.feedback_type_to_number(data.feedback_type)
    JobApplicationWithdrawal.objects.create(job_post=application.job_post,
                                            talent=user.talent, feedback_type=feedback_type, feedback=data.feedback)
    application.delete()
    return Response(status=200, data={"message": "Withdrawn successfully"})

@router.post("job-posts/share-via-email", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
@transaction.atomic
def share_job_post_via_email(request, data: ShareJobPostViaEmailSchema):
    if not data.job_posts:
        raise HttpError(400, "No job posts selected")
    if not data.emails:
        raise HttpError(400, "No emails selected")
    async_task(tasks.share_job_via_email,
        job_post_ids=data.job_posts, emails=data.emails
    )
    return Response(status=200, data={"message": "Shared successfully"})

@router.post("job-posts/share-via-chat", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
@transaction.atomic
def share_job_post_via_chat(request, data: ShareJobPostViaChatSchema):
    user = request.user
    if not data.talents:
        raise HttpError(400, "No talents selected")
    if not data.job_posts:
        raise HttpError(400, "No job posts selected")
    async_task(tasks.send_shared_job_chat,
        job_post_ids=data.job_posts, talent_ids=data.talents, sender_id=user.id
    )
    return Response(status=200, data={"message": "Shared successfully"})



@router.post("talent/job-posts/{job_post_id}/save", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
def save_job(request, job_post_id:UUID):
    IsTalentUser.check(request)
    talent = request.user.talent
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    if talent.savedjob_set.filter(job_post=job_post).exists():
        raise HttpError(400, "Already saved")
    SavedJob.objects.create(job_post=job_post, talent=talent)
    return Response(status=200, data={"message": "Saved successfully"})

@router.post("talent/job-posts/{job_post_id}/discard", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
def discard_saved_job(request, job_post_id:UUID):
    IsTalentUser.check(request)
    talent = request.user.talent
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    saved_job = talent.savedjob_set.filter(job_post=job_post).first()
    if not saved_job:
        raise HttpError(404, "This job post is not saved")
    saved_job.delete()
    return Response(status=200, data={"message": "Discarded successfully"})


