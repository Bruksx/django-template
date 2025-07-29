import logging
from typing import List
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import is_aware
from ninja.errors import HttpError

from accounts.models import Skill
from core.models import Language
from jobs.enums import PhaseType, JobStatusType, QuestionTypeEnum
from jobs.models import (
    JobApplication, Answer, RequiredAttribute, ScreeningQuestion, Job, RequiredSecondaryLanguage,
    RequiredSkill, BusinessModel, JobPost, QuestionOption
)
from jobs.schemas import ApplyToJobSchema, MutateRequiredAttributeSchema, QuestionOptionSchema, MutateOptionSchema
from ninja.errors import HttpError
from notification.notifications import send_talents_job_matching_notification
from settings.models import WorkFlowStage
from helpers.utils import upload_to_s3, upload_to_server, sort_params_function
from monkeypatches.q_cluster import async_task


def get_talent_job_recommendations(talent, business=None, search=""):
    queryset = talent.job_post_matches(by_talent_country=False, business=business)
    if search:
        queryset = queryset.filter(job__role__name__icontains=search)
    return queryset.order_by("-created_at")


def reject_application(application, previous_stage, job_post=None):
    if not job_post:
        job_post = application.job_post
    rejected_stage = WorkFlowStage.objects.filter(
        phase=PhaseType.REJECTED.value,
        created_by__business=job_post.job.created_by.business
    ).order_by("order").first()
    application.update(stage=rejected_stage)
    email = job_post.recruiter.user.email if job_post.recruiter else None
    if not email:
        email = job_post.job.created_by.user.email if job_post.job.created_by else None
    send_email_on_stage_update(application=application, previous_stage=previous_stage, business_user_email="1840 GTC")

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
        reject_application(application, stage, job_post)
        return


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
        reject_application(application, stage, job_post)
        return
    send_email_on_stage_update(application=application, business_user_email="1840 GTC")
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

def create_job_post_service(business_user, job, job_posts_data:list):
    job_posts = list()
    for data in job_posts_data:
        if "status" in data:
            data["status"] = data["status"].value
            if data["status"] == JobStatusType.POSTED.value:
                data["posted_by"] = business_user

        job_posts.append(JobPost(**data, job=job))
    if len(job_posts) == 1:
        job_posts[0].save()
        return job_posts[0]
    JobPost.objects.bulk_create(job_posts)
    return

def update_job_post_service(job_post, business_user, data=None, status=None, raise_error=False):
    new_job = None
    if not data:
        data = dict()

    if not status and "status" in data:
        status = data.get("status").value
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

def bulk_job_posts_service(job, job_post_data, business_user):
    new_job_posts = [dt for dt in job_post_data if not dt.get("uid")]
    job_post_data = {dt.pop("uid"): dt for dt in job_post_data if dt.get("uid")}
    for job_post in JobPost.objects.filter(uid__in=job_post_data.keys()).iterator():
        update_job_post_service(job_post, business_user=business_user, data=job_post_data[job_post.uid])
    create_job_post_service(business_user=business_user, job=job, job_posts_data=new_job_posts)
    return

def update_bulk__job_posts_service(business_user, job_posts_id, action):
    for job_post in JobPost.objects.filter(uid__in=job_posts_id, job__created_by__business=business_user.business).iterator():
        update_job_post_service(job_post, business_user, status=action.value)


def send_email_on_stage_update(application:JobApplication, business_user_email, previous_stage=None):
    if not business_user_email:
        return
    if not application:
        return
    if not application.stage:
        return
    if previous_stage == application.stage:
        return
    if application.stage.email_template:
        return
    context = application.get_email_context()
    application.stage.email_template.send_email(
        context=context,
        to=[application.applicant.user.email],
        sender=business_user_email
    )
    return


def validate_screening_questions(question, question_data):
    try:
        if not question:
            raise HttpError(404, "This question does not exist")

        if "type" in question_data:
            error = validate_screening_question_options(question, [MutateOptionSchema(**o) for o in question_data.get("options", list())], question_data["type"].value)
            if error:
                raise error
        return (question, question_data), None
    except Exception as e:
        return None, e


def validate_screening_question_options(question, data, question_type):
    try:
        if not question:
            raise HttpError(404, "This question does not exist")

        if question_type in (QuestionTypeEnum.FILE.value, QuestionTypeEnum.TEXT.value) and data:
            raise HttpError(400, "This question type does not support options")

        question_options = question.questionoption_set.all()
        new_options = [option for option in data if not option.uid]
        changing_options = [option for option in data if option.uid]
        changing_options_id = (option.uid for option in changing_options)
        existing_options = question_options.exclude(uid__in=changing_options_id)
        if question_type == QuestionTypeEnum.SINGLE_SELECT.value:
            new_correct_option = [option for option in new_options if option.is_accepted is True]
            changing_correct_option = [option for option in changing_options if option.is_accepted is True]
            correct_option = new_correct_option + changing_correct_option
            if (len(correct_option) + existing_options.filter(is_accepted=True).count()) != 1:
                raise HttpError(400, "Single select question must have exactly one correct option")
        if question_type == QuestionTypeEnum.MULTI_SELECT.value:
            new_correct_options = [option for option in new_options if option.is_accepted is True]
            changing_correct_options = [option for option in changing_options if option.is_accepted is True]
            correct_options = new_correct_options + changing_correct_options
            if (len(correct_options) + existing_options.filter(is_accepted=True).count()) < 2:
                raise HttpError(400, "Multiple select question must have at least two correct options")
        return
    except Exception as e:
        return e

def update_screening_question_options(question, data:List[MutateOptionSchema]):
    if not question:
        return None, HttpError(404, "This question does not exist")
    error = validate_screening_question_options(question, data, question.type)
    if error:
        return None, error
    for option in data:
        if not option.uid:
            opt_data = option.dict()
            opt_data.pop("uid", None)
            QuestionOption.objects.create(question=question, **opt_data)
        else:
            question.questionoption_set.filter(uid=option.uid).update(**option.dict())
    return question, None
