import logging
from typing import List

from ninja.errors import HttpError

from jobs.enums import PhaseType
from jobs.models import JobApplication, Answer, AnswerAttachment
from jobs.schemas import MutateAnswerSchema
from settings.models import WorkFlowStage


def get_talent_job_recommendations(talent, search="", use_filter=False, **kwargs):
    queryset = talent.job_post_matches()
    logging.critical(f"Queryset: {queryset}")
    if search:
        queryset = queryset.filter(job__title__icontains=search)
    if use_filter:
        if not hasattr(talent, "jobfilter"):
            raise HttpError(400, "You have not set a job filter yet")
        queryset = talent.jobfilter.get_queryset(queryset)
    return queryset.order_by("-created_at")


def create_job_application(job_post, talent, data:List[MutateAnswerSchema]):
    application = JobApplication.objects.create(job_post=job_post, applicant=talent,
                                                recruiter=job_post.recruiter,
                                                match=talent.job_match_score(job_post))
    for answer in data:
        answer = Answer(application=application,
                        question=answer.question, text=answer.text)
        if answer.options:
            answer.options.set(answer.options)
        answer.save()
        if answer.files:
            AnswerAttachment.objects.bulk_create([
                AnswerAttachment(answer=answer, file=file) for file in answer.files
            ])
        answer.score = answer.get_score()
        answer.save(["score"])
    score = application.get_screening_test_score()
    if score and score == 0:
        rejected_stage = WorkFlowStage.objects.filter(phase=PhaseType.REJECTED.value).order_by("order").first()
        application.update(stage=rejected_stage)
    return