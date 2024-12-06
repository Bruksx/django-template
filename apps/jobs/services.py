from ninja.errors import HttpError


def get_talent_job_recommendations(talent, search="", use_filter=False, **kwargs):
    queryset = talent.job_post_matches()
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        if not hasattr(talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-created_at")
