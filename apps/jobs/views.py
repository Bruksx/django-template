import logging
from typing import List

from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate
from ninja_jwt.authentication import JWTAuth

from jobs.schemas import TalentJobPostListSchema

router = Router(auth=JWTAuth())

@router.get("talent/job-recommendations", response=List[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(pass_parameter="pagination_info")
def talent_job_recommendations(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    pagination = kwargs["pagination_info"]
    limit = pagination.limit
    offset = pagination.offset
    start = limit * offset
    end = limit * (offset + 1)
    queryset = user.talent.job_post_matches()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        queryset = user.talent.jobfilter.get_queryset(queryset)
    queryset = queryset[start:end]
    return [TalentJobPostListSchema.model_validate(post, context=dict(talent=user.talent)) for post in queryset]


@router.get("talent/saved-jobs", response=List[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(pass_parameter="pagination_info")
def talent_saved_jobs(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    pagination = kwargs["pagination_info"]
    limit = pagination.limit
    offset = pagination.offset
    start = limit * offset
    end = limit * (offset + 1)
    queryset = user.talent.saved_jobs()[start: end]
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        queryset = user.talent.jobfilter.get_queryset(queryset)
    queryset = queryset[start:end]
    return [TalentJobPostListSchema.model_validate(post, context=dict(talent=user.talent)) for post in queryset]


@router.get("talent/applied-jobs", response=List[TalentJobPostListSchema], tags=["Talent Dashboard"])
@paginate(pass_parameter="pagination_info")
def talent_applied_jobs(request, search="", use_filter=False, **kwargs):
    user = request.user
    if not hasattr(user, "talent"):
        return HttpError(403, "Only Talents are allowed")
    pagination = kwargs["pagination_info"]
    limit = pagination.limit
    offset = pagination.offset
    start = limit * offset
    end = limit * (offset + 1)
    queryset = user.talent.applied_jobs()[start: end]
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        queryset = user.talent.jobfilter.get_queryset(queryset)
    queryset = queryset[start:end]
    return [TalentJobPostListSchema.model_validate(post, context=dict(talent=user.talent)) for post in queryset]
