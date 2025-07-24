from datetime import time, datetime, timezone, tzinfo
from typing import List, Optional, Any
from uuid import UUID

import pytz
from config import settings
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.timezone import is_aware
from helpers.utils import upload_to_s3, upload_to_server
from helpers.utils import sort_params_function
from ninja.errors import HttpError

from accounts.models import Skill
from core.models import Language
from jobs.enums import PhaseType
from jobs.models import (
    JobApplication, Answer, RequiredAttribute, ScreeningQuestion, Job, RequiredSecondaryLanguage, 
    RequiredSkill, BusinessModel, 
)
from jobs.schemas import ApplyToJobSchema, MutateRequiredAttributeSchema
from notification.notifications import send_talents_job_matching_notification
from settings.models import WorkFlowStage

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


def set_job_required_attributes(data:dict, job: Job):
    MutateRequiredAttributeSchema.validate_required_attribute(data, job)
    required_attributes, _ = RequiredAttribute.objects.get_or_create(job=job)
    skill_uids = data.pop("skills")
    business_model_uids = data.pop("business_models", [])
    secondary_language_uids = data.pop("secondary_languages", [])
    skills = []
    for uid in skill_uids:
        skill = Skill.objects.filter(uid=uid).first()
        rs = RequiredSkill(
            required_attribute=job.requiredattribute,
            skill=skill,
        )
        skills.append(rs)
    RequiredSkill.objects.bulk_create(skills)

    required_attributes.business_models.exclude(uid__in=business_model_uids).delete()
    for uid in business_model_uids:
        if not required_attributes.business_models.filter(uid=uid).exists():
            business_model = get_object_or_404(BusinessModel, uid=uid)
            required_attributes.business_models.add(business_model)
    

    RequiredSecondaryLanguage.objects.exclude(uid__in=secondary_language_uids).delete()
    for uid in secondary_language_uids:
        language = get_object_or_404(Language, uid=uid)
        RequiredSecondaryLanguage.objects.get_or_create(
            required_attribute=required_attributes,
            language=language
        )
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
