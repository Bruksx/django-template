from uuid import UUID

from django.db import transaction
from django_q.tasks import async_task
from ninja import Router, PatchDict
from ninja.errors import HttpError
from ninja.responses import Response
from ninja_extra.pagination import PageNumberPaginationExtra, paginate
from ninja_extra.schemas import PaginatedResponseSchema
from ninja_jwt.authentication import JWTAuth

from jobs import tasks
from jobs.models import JobFilter, JobApplication, JobPost, JobApplicationWithdrawal, SavedJob
from jobs.schemas import TalentJobPostListSchema, TalentJobFilterSchema, MutateTalentJobFilterSchema, \
    TalentJobApplySchema, TalentJobApplicationWithdrawalSchema, ShareJobPostViaEmailSchema, ShareJobPostViaChatSchema

router = Router()

@router.get("talent/job-recommendations", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_job_recommendations(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    queryset = user.talent.job_post_matches()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        if not hasattr(user.talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = user.talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-created_at")

@router.get("talent/saved-jobs", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_saved_jobs(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    queryset = user.talent.saved_jobs()
    if search:
        if not hasattr(user.talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        queryset = user.talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-savedjob__created_at")

@router.get("talent/job-posts", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def job_posts_by_talent_country(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    queryset = JobPost.objects.filter(country=user.talent.country, is_posted=True)
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        if not hasattr(user.talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = user.talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-created_at")

@router.get("talent/applied-jobs", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_applied_jobs(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    queryset = user.talent.applied_jobs()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        if not hasattr(user.talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = user.talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-jobapplication__created_at")


@router.patch("talent/job-filter", auth=JWTAuth(), tags=["Talent Jobs"], response=TalentJobFilterSchema)
def update_talent_job_filter(request, data: PatchDict[MutateTalentJobFilterSchema]):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    if "location_type" in data:
        data["location_type"] = data["location_type"].value
    if not hasattr(user.talent, "jobfilter"):
        JobFilter.objects.create(talent=user.talent, **data)
    else:
        user.talent.jobfilter.update(**data)
    user.talent.refresh_from_db()
    return user.talent.jobfilter

@router.get("talent/job-filter", auth=JWTAuth(), tags=["Talent Jobs"], response=TalentJobFilterSchema)
def get_talent_job_filter(request):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    if not hasattr(user.talent, "jobfilter"):
        raise HttpError(400, "You have not set a job filter yet")
    return user.talent.jobfilter


@router.post("talent/job-posts/{job_post_id}/apply", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
def apply_to_job_post(request, job_post_id:UUID, data: PatchDict[TalentJobApplySchema]):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    if not job_post.is_posted:
        raise HttpError(400, "Job post is no longer available")
    if JobApplication.objects.filter(job_post=job_post, applicant=user.talent).exists():
        raise HttpError(400, "Already applied")
    JobApplication.objects.create(job_post=job_post_id, applicant=user.talent,
                                  recruiter=job_post.recruiter,
                                 **data, match=user.talent.job_match_score(job_post))
    return Response(status=200, data={"message": "Applied successfully"})


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

@router.post("talent/job-posts/{job_post_id}/share-via-email", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
@transaction.atomic
def share_job_post_via_email(request, job_post_id:UUID, data: ShareJobPostViaEmailSchema):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    async_task(tasks.send_shared_job_email,
        job_post_id=job_post.id, emails=data.emails
    )
    return Response(status=200, data={"message": "Shared successfully"})

@router.post("talent/job-posts/{job_post_id}/share-via-chat", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
@transaction.atomic
def share_job_post_via_chat(request, job_post_id:UUID, data: ShareJobPostViaChatSchema):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    async_task(tasks.send_shared_job_chat,
        job_post_id=job_post.id, talent_ids=data.talent_ids, sender_id=user.id
    )
    return Response(status=200, data={"message": "Shared successfully"})



@router.post("talent/job-posts/{job_post_id}/save", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
def save_job(request, job_post_id:UUID):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    if user.talent.savedjob_set.filter(job_post=job_post).exists():
        raise HttpError(400, "Already saved")
    SavedJob.objects.create(job_post=job_post, talent=user.talent)
    return Response(status=200, data={"message": "Saved successfully"})

@router.post("talent/job-posts/{job_post_id}/discard", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
def discard_saved_job(request, job_post_id:UUID):
    user = request.user
    if not hasattr(user, "talent"):
        raise HttpError(403, "Only Talents are allowed")
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    saved_job = user.talent.savedjob_set.filter(job_post=job_post).first()
    if not saved_job:
        raise HttpError(404, "This job post is not saved")
    saved_job.delete()
    return Response(status=200, data={"message": "Discarded successfully"})





