from typing import List
from uuid import UUID

from django_q.tasks import async_task
from ninja import Router, PatchDict
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth

from jobs import tasks
from jobs.models import JobFilter, JobApplication, JobPost, JobApplicationWithdrawal, SavedJob
from jobs.schemas import TalentJobPostListSchema, TalentJobFilterSchema, \
    TalentJobApplySchema, TalentJobApplicationWithdrawalSchema, ShareJobPostViaEmailSchema

router = Router()

@router.get("talent/job-recommendations", auth=JWTAuth(), response=List[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate
def talent_job_recommendations(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    queryset = user.talent.job_post_matches()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        queryset = user.talent.jobfilter.get_queryset(queryset)
    return queryset

@router.get("talent/saved-jobs", auth=JWTAuth(), response=List[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate
def talent_saved_jobs(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    queryset = user.talent.saved_jobs()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        queryset = user.talent.jobfilter.get_queryset(queryset)
    return queryset

@router.get("talent/applied-jobs", auth=JWTAuth(), response=List[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate
def talent_applied_jobs(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    queryset = user.talent.applied_jobs()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        queryset = user.talent.jobfilter.get_queryset(queryset)
    return queryset


@router.patch("talent/job-filter", auth=JWTAuth(), tags=["Talent Jobs"])
def update_talent_job_filter(request, data: PatchDict[TalentJobFilterSchema]):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    if not hasattr(user.talent, "jobfilter"):
        JobFilter.objects.create(talent=user.talent, **data)
    else:
        user.talent.jobfilter.update(**data)
    return Response(status=200, data={"message": "Job filter updated successfully"})


@router.post("talent/job-posts/{job_post_id}/apply", response={200: None}, tags=["Talent Jobs"])
def apply_to_job_post(request, job_post_id:UUID, data: PatchDict[TalentJobApplySchema]):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    if JobApplication.objects.filter(job_post=job_post, applicant=user.talent).exists():
        raise HttpError(400, "Already applied")
    JobApplication.objects.create(job_post_id=job_post_id, applicant=user.talent,
                                 **data, match=user.talent.job_match_score(job_post))
    return Response(status=200, data={"message": "Applied successfully"})


@router.post("talent/job-posts/applications/{application_id}/withdraw", response={200: None}, tags=["Talent Jobs"])
def withdraw_job_applications(request, application_id:UUID, data: PatchDict[TalentJobApplicationWithdrawalSchema]):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    application = JobApplication.objects.filter(uid=application_id).first()
    if not application:
        raise HttpError(404, "Application not found")
    JobApplicationWithdrawal.objects.create(job_post=application.job_post,
                                            talent=user.talent, **data)
    application.delete()
    return Response(status=200, data={"message": "Withdrawn successfully"})

@router.post("talent/job-posts/{job_post_id}/share-via-email", response={200: None}, tags=["Talent Jobs"])
def share_job_post_via_email(request, job_post_id:UUID, data: ShareJobPostViaEmailSchema):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    async_task(tasks.send_shared_job_email(
        job_post_id=job_post.id, talent_ids=data.talents, emails=data.emails
    ))
    return Response(status=200, data={"message": "Shared successfully"})

@router.post("talent/job-posts/{job_post_id}/save", response={200: None}, tags=["Talent Jobs"])
def save_job(request, job_post_id:UUID):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    job_post = JobPost.objects.filter(uid=job_post_id).first()
    if not job_post:
        raise HttpError(404, "Job post not found")
    if user.talent.savedjob_set.filter(job_post=job_post).exists():
        raise HttpError(400, "Already saved")
    SavedJob.objects.create(job_post=job_post, talent=user.talent)
    return Response(status=200, data={"message": "Saved successfully"})






