from typing import List, Literal
from uuid import UUID

from config.permissions import IsTalentUser, IsBusinessUser
from django.db import transaction
from monkeypatches.q_cluster import async_task
from monkeypatches.response import Response
from ninja import Router, PatchDict, UploadedFile
from ninja.errors import HttpError
from ninja.params import Query
from ninja_extra.pagination import paginate
from ninja_jwt.authentication import JWTAuth

from accounts.models import Talent
from jobs import tasks
from jobs.enums import JobStatusType
from jobs.models import JobFilter, JobApplication, JobPost, JobApplicationWithdrawal, SavedJob, JobAlert
from jobs.schemas import TalentJobPostListSchema, TalentJobFilterSchema, MutateTalentJobFilterSchema, \
    TalentJobApplicationWithdrawalSchema, TalentJobPostSchema, AppliedTalentJobPostListSchema, ApplyToJobSchema, \
    ShareJobViaEmailSchema, ShareJobViaChatSchema, JobPostFilterSchema
from jobs.services import get_talent_job_recommendations, create_job_application, upload_answer_files_service, \
    order_job_posts
from notification import notifications
from paginations import CustomPageNumberPaginationExtra as PageNumberPaginationExtra
from paginations import CustomPaginatedResponseSchema as PaginatedResponseSchema

router = Router()

@router.get("talent/job-recommendations", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def logged_in_talent_job_recommendations(request, filters:JobPostFilterSchema = Query(...)):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = {"talent": talent}
    queryset = get_talent_job_recommendations(talent, filters.search)
    if filters.sort_by:
        sorts = filters.sort_by.split(",")
        return order_job_posts(sorts, queryset)
    return queryset

@router.get("talents/{talent_uid}/job-recommendations", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_job_recommendations(request, talent_uid:UUID, filters:JobPostFilterSchema = Query(...)):
    IsBusinessUser.check(request)
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "Talent not found")
    request.context = {"talent": talent}
    queryset = get_talent_job_recommendations(talent, filters.search)
    if filters.sort_by:
        sorts = filters.sort_by.split(",")
        return order_job_posts(sorts, queryset)
    return queryset

@router.get("talent/saved-jobs", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_saved_jobs(request, filters:JobPostFilterSchema = Query(...)):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = {"talent": talent}
    queryset = talent.saved_jobs()
    if filters.search:
        queryset = queryset.filter(job__title__icontains=filters.search)
    if hasattr(talent, "jobfilter"):
           queryset = talent.jobfilter.get_queryset(queryset)
    if filters.sort_by:
        sorts = filters.sort_by.split(",")
        return order_job_posts(sorts, queryset)
    return queryset.order_by("-savedjob__created_at")

@router.get("talent/job-posts", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def job_posts_by_talent_country(request, filters:JobPostFilterSchema = Query(...)):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = {"talent": talent}
    queryset = JobPost.objects.filter(country=talent.country, status=JobStatusType.POSTED.value)
    if filters.search:
        queryset = queryset.filter(job__title__icontains=filters.search)
    if hasattr(talent, "jobfilter"):
        queryset = talent.jobfilter.get_queryset(queryset)
    if filters.sort_by:
        sorts = filters.sort_by.split(",")
        return order_job_posts(sorts, queryset)
    return queryset.order_by("-created_at")

@router.get("talent/applied-jobs", auth=JWTAuth(), response=PaginatedResponseSchema[AppliedTalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(PageNumberPaginationExtra, page_size=50)
def talent_applied_jobs(request, filters: JobPostFilterSchema = Query(...)):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = {"talent": talent}
    queryset = talent.applied_jobs()
    if filters.search:
        queryset = queryset.filter(job__title__icontains=filters.search)
    if hasattr(talent, "jobfilter"):
        queryset = talent.jobfilter.get_queryset(queryset)
    if filters.sort_by:
        sorts = filters.sort_by.split(",")
        return order_job_posts(sorts, queryset)
    return queryset.order_by("-jobapplication__created_at")


@router.patch("talent/job-filter", auth=JWTAuth(), tags=["Talent Jobs"], response=TalentJobFilterSchema)
def update_talent_job_filter(request, data: PatchDict[MutateTalentJobFilterSchema]):
    IsTalentUser.check(request)
    talent = request.user.talent
    if "location_type" in data and data.get("location_type"):
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
        JobFilter.objects.create(talent=talent)
    return talent.jobfilter


@router.post("talent/job-posts/{job_post_id}/apply", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
@transaction.atomic
def apply_to_job_post(request, job_post_id:UUID, data: ApplyToJobSchema):
    IsTalentUser.check(request)
    talent = request.user.talent
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    if job_post.status != JobStatusType.POSTED.value:
        raise HttpError(400, "Job post is no longer available")
    if JobApplication.objects.filter(job_post=job_post, applicant=talent).exists():
        raise HttpError(400, "Already applied")
    create_job_application(job_post=job_post, talent=talent, data=data)
    return Response(status=200, data={"message": "Applied successfully"})

@router.post("talent/job-posts/answer-files", response={200: None}, tags=["Talent Jobs"])
def upload_answer_files(request, files:List[UploadedFile]):
    # IsTalentUser.check(request)
    file_urls = upload_answer_files_service(files=files)
    return Response(status=200, data=dict(message="Files uploaded successfully", data=file_urls))



@router.get("talent/job-posts/{job_post_id}", auth=JWTAuth(),
             description="this will notify the business connected to the job post if there is a match",
             response=TalentJobPostSchema, tags=["Talent Jobs"])
def view_job_post(request, job_post_id:UUID):
    IsTalentUser.check(request)
    talent = request.user.talent
    request.context = dict(talent=talent)
    job_post:JobPost = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    job_post.view()
    notifications.send_talent_job_matching_notification(talent, job_post)
    return job_post


@router.get("talent/job/{job_id}", auth=JWTAuth(),
             description="view job posts from job alert",
             response=TalentJobPostSchema, tags=["Talent Jobs"])
def view_job_from_alert(request, job_id:UUID):
    IsTalentUser.check(request)
    talent = request.user.talent
    job_post:JobPost = JobPost.objects.filter(job__uid=job_id, country=talent.country).last()
    if not job_post:
        raise HttpError(404, "This job is not available in your country")
    job_post.view()
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

@router.post("share/via-email", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
@transaction.atomic
def share_jobs_via_email(request, data: ShareJobViaEmailSchema):
    if not data.jobs:
        raise HttpError(400, "No jobs selected")
    if not data.emails:
        raise HttpError(400, "No emails selected")
    async_task(tasks.share_job_via_email,
        job_ids=data.jobs, emails=data.emails
    )
    return Response(status=200, data={"message": "Shared successfully"})

@router.post("share/via-chat", auth=JWTAuth(), response={200: None}, tags=["Talent Jobs"])
@transaction.atomic
def share_jobs_via_chat(request, data: ShareJobViaChatSchema):
    user = request.user
    if not data.talents:
        raise HttpError(400, "No talents selected")
    if not data.jobs:
        raise HttpError(400, "No jobs selected")
    async_task(tasks.send_shared_job_chat,
        job_ids=data.jobs, talent_ids=data.talents, sender_id=user.id
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


@router.post("talent/job-posts/{job_post_id}/alert", auth=JWTAuth(), tags=["Talent Jobs"])
def set_job_alert(request, job_post_id:UUID, action: Literal["on", "off"]):
    IsTalentUser.check(request)
    talent = request.user.talent
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    if not hasattr(talent, "jobalert"):
        alert = JobAlert.objects.create(talent=talent)
    else:
        alert = talent.jobalert
    if action == "on" and not alert.jobs.filter(id=job_post.job_id).exists():
        alert.jobs.add(job_post.job)
        alert.save()
    elif alert == "off" and alert.jobs.filter(id=job_post.job_id).exists():
        alert.jobs.remove(job_post.job)
        alert.save()
    message = "set" if action == "on" else "unset"
    return Response(status=200, data={"message": f"Job alert has been {message} for this job successfully"})


