import logging
from io import BytesIO
from typing import List
from uuid import UUID

from accounts.models import Skill
from core.models import Language
from django.conf import settings
from django.contrib.postgres.aggregates import StringAgg
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import QuerySet, Window, F, Q, OuterRef, Exists, Count, Case, When, Value, Func, \
    CharField
from django.db.models.functions import RowNumber, Cast, Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from jobs.enums import PhaseType, JobStatusType, QuestionTypeEnum
from jobs.models import (
    JobApplication, Answer, RequiredAttribute, ScreeningQuestion, Job, RequiredSecondaryLanguage,
    RequiredSkill, BusinessModel, JobPost, QuestionOption, JobPostTag, TalentApplicationStageTimeline,
    JobPostExport,
)
from jobs.schemas import ApplyToJobSchema, MutateRequiredAttributeSchema, MutateOptionSchema, BusinessJobFilterSchema
from ninja.errors import HttpError
from notification.notifications import send_talents_job_matching_notification
from openpyxl import Workbook
from settings.models import WorkFlowStage

from config.settings import FRONTEND_URL
from helpers.utils import upload_to_s3, upload_to_server, sort_params_function, export_rows_to_excel
from monkeypatches.q_cluster import async_task


def get_talent_job_recommendations(talent, business=None, search="", distinct=False, by_talent_role=False):
    queryset = talent.job_post_matches(by_talent_country=True, business=business, by_talent_role=by_talent_role)
    if search not in (None, ""):
        queryset = queryset.filter(job__role__name__icontains=search)
    if distinct is True:
        queryset = queryset.annotate(
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F("job_id")],
                order_by=[F("computed_match_score").desc()]  # highest score first
            )
        ).filter(row_number=1)
    return queryset.order_by("-refresh_order", "-posted_order")


def reject_application(application, previous_stage, job_post=None):
    if not job_post:
        job_post = application.job_post
    rejected_stage = WorkFlowStage.objects.filter(
        phase=PhaseType.REJECTED.value,
        created_by__business=job_post.job.created_by.business
    ).order_by("order").first()
    application.update(stage=rejected_stage)
    send_email_on_stage_update(application=application, previous_stage=previous_stage)

@transaction.atomic
def create_job_application(job_post, talent, data:ApplyToJobSchema):
    stage = (WorkFlowStage.objects.filter(phase=PhaseType.NEW.value, created_by__business=job_post.job.created_by.business)
             .order_by("order").first())
    application = JobApplication.objects.create(job_post=job_post, applicant=talent,
                                                recruiter=job_post.recruiter,
                                                stage=stage,
                                                available_for_schedule=data.available_for_schedule)
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
    send_email_on_stage_update(application=application)
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


def order_job_posts(queryset, sorts:List[str]=None, *extra_sort_params:List[str], distinct=False)->QuerySet:
    """
    sort job posts

    Args:
        queryset: job posts queryset
        sorts: list of sort parameters based on API query
        *extra_sort_params: extra sort parameters based on model fields
        distinct: distinct job posts
    """
    mapper = {"date-posted": "date_posted", "job-level": "job__job_level", "match-score": "computed_match_score"}
    sort_values = []
    if sorts:
        sort_values = sort_params_function(sorts, mapper)
    if not sort_values:
        sort_values = ["-refresh_order", "-posted_order", *extra_sort_params]
    if distinct is True:
        return queryset.annotate(
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F("job_id")],
                order_by=[F("computed_match_score").desc()]  # highest score first
            )
        ).filter(row_number=1).order_by(*sort_values)
    try:
        if queryset.count() > 0:
            logging.critical(f"annotations: {queryset[0].computed_match_score}")
    except:
        logging.critical("annotations: annotations not computed")
    return queryset.order_by(*sort_values)


def get_screening_questions_service(request, job_uid:UUID):
    if not Job.objects.filter(uid=job_uid, created_by__business=request.user.businessuser.business).exists():
        raise HttpError(404, "This job does not exist")
    screening_questions = ScreeningQuestion.objects.filter(job__uid=job_uid)
    return screening_questions.filter(job__created_by__business=request.user.businessuser.business)

def create_job_post_service(business_user, job, job_posts_data:list):
    job_post = None
    for data in job_posts_data:
        tags = data.pop("tags", list())
        if "status" in data:
            data["status"] = data["status"].value
            if data["status"] == JobStatusType.POSTED.value:
                data["posted_by"] = business_user
        if data.get("salary_type"):
            data["salary_type"] = data["salary_type"].value if type(data["salary_type"]) is not str else \
                data[
                    "salary_type"]
        if data.get("salary_bonus_type"):
            data["salary_bonus_type"] = data["salary_bonus_type"].value if type(
                data["salary_bonus_type"]) is not str else data["salary_bonus_type"]
        
        job_post = JobPost.objects.create(**data, job=job)
        handle_job_post_tags(job_post, tags, business_user.business)
    if len(job_posts_data) == 1:
        return job_post
    return

def update_job_post_service(job_post, business_user, data=None, status=None, raise_error=False):
    new_job_post = None
    if not data:
        data = dict()
    data["edited_by"] = business_user
    data["edited_at"] = timezone.now()
    tags = None
    if "tags" in data:
        tags = data.pop("tags")
    if not status and "status" in data:
        status = data.get("status").value
    if status:
        data["status"] = status
        if job_post.status != status and status == JobStatusType.POSTED.value:
            data["posted_by"] = business_user
        
        if status == JobStatusType.DRAFT.value and job_post.status != JobStatusType.DRAFT.value:
            # you're trying to prevent editing job posts with applications
            new_job_post = job_post.copy()
    if data.get("salary_type"):
        data["salary_type"] = data["salary_type"].value if type(data["salary_type"]) is not str else \
        data[
            "salary_type"]

    if data.get("salary_bonus_type"):
        data["salary_bonus_type"] = data["salary_bonus_type"].value if type(
            data["salary_bonus_type"]) is not str else data["salary_bonus_type"]
    if new_job_post:
        job_post.update(status=JobStatusType.CLOSED.value)
        new_job_post.update(**data)
        if tags:
            new_job_post = handle_job_post_tags(new_job_post, tags, business_user.business)
        return new_job_post

    job_post = job_post.update(**data)
    if tags:
        job_post = handle_job_post_tags(job_post, tags, business_user.business)
    return job_post

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


def send_email_on_stage_update(application:JobApplication, business_user=None, previous_stage=None):
    if not business_user:
        business_user = application.recruiter
    if business_user:
        business_user_email = business_user.user.email
    else:
        business_user_email = "1840 GTC"
    if not business_user_email:
        return
    if not application:
        return
    if not application.stage:
        return
    if previous_stage == application.stage:
        return
    if not application.stage.email_template:
        return
    # retrieve email context, it should be a dictionary
    context = application.get_email_context(external_recruiter=business_user)

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
            if question.is_knockout is True and  (len(correct_option) + existing_options.filter(is_accepted=True).count()) != 1:
                raise HttpError(400, "Single select question must have exactly one correct option")
        if question_type == QuestionTypeEnum.MULTI_SELECT.value:
            new_correct_options = [option for option in new_options if option.is_accepted is True]
            changing_correct_options = [option for option in changing_options if option.is_accepted is True]
            correct_options = new_correct_options + changing_correct_options
            if question.is_knockout is True and  (len(correct_options) + existing_options.filter(is_accepted=True).count()) < 2:
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

def get_talents_by_job_posts_service(request, job_post, search):
    if not job_post:
        raise HttpError(404, "Job Post not found")
    request.context = dict(job_post=job_post)

    query = Q()
    if search:
        q = Q()
        for s in search.split(" "):
            if s:
                q = q | Q(user__fullname__icontains=s) | Q(user__email__icontains=s)
        query = query & q
    talents = job_post.get_talents()
    send_talents_job_matching_notification(talents.count(), job_post)
    return talents.filter(query)


def get_talent_screening_results(talent, business=None):
    queryset = JobApplication.objects.filter(applicant=talent).annotate(
        has_questions=Exists(
            ScreeningQuestion.objects.filter(job__id=OuterRef("job_post__job_id")),
        ),
        has_answers=Exists(
            Answer.objects.filter(question__job__id=OuterRef("job_post__job_id")),
        )
    ).filter(has_questions=True, has_answers=True).select_related("job_post", "job_post__job")
    if business:
        queryset = queryset.filter(job_post__job__created_by__business=business)
    return queryset


def handle_job_post_tags(job_post, tags: list[str], business):
    if not job_post:
        raise HttpError(404, "Job Post not found")
    if tags is None:
        raise HttpError(400, "Tags not found")
    if not business:
        raise HttpError(400, "Business not found")

    # Fetch existing tags once
    existing = set(
        JobPostTag.objects.filter(name__in=tags, business=business)
        .values_list("name", flat=True)
    )

    # Compute missing tags in Python (cheap)
    missing = [
        JobPostTag(name=tag, business=business)
        for tag in tags
        if tag not in existing
    ]

    # Create missing tags in one query
    if missing:
        JobPostTag.objects.bulk_create(missing)

    # Attach tags to job – fetch all matching tags once
    tag_qs = JobPostTag.objects.filter(name__in=tags, business=business)
    job_post.tags.set(tag_qs)
    job_post.save()
    return job_post

def delete_job_post_tags(tags:list[str], business):
    if not tags:
        raise HttpError(400, "Tags not found")

    # Fetch existing tags and delete
    JobPostTag.objects.filter(name__in=tags, business=business).hard_delete()

    return


def handle_stage_update(application: JobApplication, stages: List[WorkFlowStage], business_user, raise_exception=True):
    try:
        if not application:
            raise HttpError(404, "Application does not exist")
        if stages[0] == application.stage:
            forward = True
        elif stages[-1] == application.stage:
            forward = False
        else:
            raise HttpError(400, "Current stage must be the first or the last stage")
        final_stage = stages[-1] if forward else stages[0]
        previous_stage = stages[-2] if forward else stages[1]
        if not forward:
            stages = stages[::-1]

        for stage in stages:
            tf = TalentApplicationStageTimeline.objects.filter(
             application=application, stage=stage).first()

            if not tf and (forward or (not forward and stage == final_stage)):
                tf = TalentApplicationStageTimeline.objects.create(stage=stage, application=application, job_role=application.job_post.job.role)

            if not forward and tf and stage != final_stage:
                tf.delete()

            if forward and tf:
                tf.exit_date = timezone.now() if stage != final_stage else None
                tf.save()

        application.stage = final_stage
        application.stage_date_updated = timezone.now()
        application.save()
        async_task(send_email_on_stage_update, application=application, previous_stage=previous_stage,
                                   business_user=business_user)
        return application
    except Exception as e:
        if raise_exception:
            raise e
        return None


def export_job_posts_excel():
    job_posts = JobPost.objects.order_by("-job__created_at")
    wb = Workbook()
    ws = wb.active
    ws.title = "Job Posts"

    ws.append([
        "Job UID",
        "Job Title",
        "Country",
        "Province",
        "City",
    ])

    job_posts = job_posts.select_related("job", "country", "province")

    for job_post in job_posts:
        role_name = job_post.job.role.name if job_post.job.role else ""
        ws.append([
            str(job_post.uid),
            job_post.job.title or role_name,
            job_post.country.name if job_post.country else "",
            job_post.province.name if job_post.province else "",
            job_post.city,
        ])
    
    column_widths = {
        "A": 40,
        "B": 30,
        "C": 30, 
        "D": 30,
        "E": 30
    }

    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    export = JobPostExport()
    timestamp = timezone.now().strftime("%B %d, %Y at %I:%M %p")
    filename = f"job_posts_export{timestamp}.xlsx"
    export.file.save(
        filename,
        ContentFile(output.read()),
        save=True
    )

    return export

def handle_application_stage(application, business_user, stage=None, advance:bool=True, raise_exception:bool=True):
    try:
        if not stage:
            if advance is True:
                stage = application.stage.next_stages().first()
            else:
                stage = application.stage.previous_stages().last()
        if not stage:
            raise HttpError(404, "Stage not found")
        previous_stage = application.stage
        application.stage = stage
        application.stage_date_updated = timezone.now()
        application.save()
        async_task(send_email_on_stage_update, application=application, previous_stage=previous_stage,
                   business_user=business_user)
        return application
    except Exception as e:
        if raise_exception:
            raise e
        return None

def handle_applications_stage(applications, business_user, stage=None, advance:bool=True):
    for application in applications:
        async_task(handle_application_stage, application, business_user, stage, advance, raise_exception=False)

def export_job_posts_to_excel2(jobs:QuerySet[Job], background:bool=False):
    title = "Job Posts"
    headers = [
        "UID",
       "Role",
       "Client",
       "Location",
       "Applicants",
       "Status",
       "Recruiter",
       "Date Posted"
    ]
    rows = []
    bold_rows = []
    count = 2
    for job in jobs.select_related("role").annotate(
        role_name=Case(
            When(role__isnull=True, then=Value("")),
            default="role__name",
        )
    ).order_by("-created_at"):
        job_posts = job.jobpost_set.select_related("country", "recruiter__user").annotate(
            applicants=Count("jobapplication"),
            recruiter_name=Case(
                When(recruiter__isnull=True, then=Value("")),
                default="recruiter__user__fullname",
            ),
            date_posted_excel=Case(
                When(created_at__isnull=True, then=Value("")),
                default=Func(
                    'date_posted',
                    function='TO_CHAR',
                    template="TO_CHAR(%(expressions)s, 'DD-MM-YYYY')",
                    output_field=CharField()
                )
            ),
            uid_str=Cast("uid", output_field=CharField()),

        ).distinct().values_list("uid_str","country__name", "applicants", "status", "recruiter_name", "date_posted_excel")
        job_post_count = job_posts.count()
        rows.append([
            "Job",
            job.role_name,
            job.hiring_company_name,
            job_posts.first()[1] if job_post_count == 1 else "Multiple",
            JobApplication.objects.filter(job_post__job_id=job.id).count(),
            job_posts.first()[3] if job_post_count == 1 else "Multiple",
            job_posts.first()[4] if job_post_count == 1 else "Multiple",
            job_posts.first()[5] if job_post_count == 1 else "Multiple" ,

        ])
        bold_rows.append(count)
        count += 1
        for job_post in job_posts:
            rows.append([job_post[0],job.role_name, job.hiring_company_name, *job_post[1:]])
            count += 1
        rows.append(["", "", "", "", "", "", "", ""])
        count += 1

    return export_rows_to_excel(rows=rows, headers=headers, title=title, bold_rows=bold_rows, background=background)

def export_job_posts_to_excel(context, background:bool=False):
    job_url = lambda job_post_uid: f"{FRONTEND_URL}jobs-listing/{job_post_uid}"
    title = "Job Posts"
    headers = [
        "Posting ID",
        "Role",
        "Date Created (UTC)",
        "Status (Posted/Paused/Draft/Closed)",
        "Tags",
        "Linkedin Tag",
        "Employment Type",
        "Hiring Company",
        "Department",
        "Work Structure (Remote/Hybrid/Onsite)",
        "Primary Location",
        "State Province or Territory",
        "City",
        "Postal Code",
        "Assign Recruiter",
        "Application",
        "External Link/ Job Application Link",
        "Internal Notes"

    ]
    empty_header = [" " for _ in headers]
    rows = []
    job_posts = BusinessJobFilterSchema.filter_job_posts(
        context, JobPost.objects.select_related("job",
       "job__role", "job__employment_type", "job__department",
        "country", "province", "recruiter__user").all())
    job_posts = job_posts.annotate(
        applicants=Count("jobapplication"),
        role=Case(
            When(job__role__isnull=True, then=Value('')),
            default="job__role__name"
        ),
        recruiter_name=Case(
            When(recruiter__isnull=True, then=Value("")),
            default="recruiter__user__fullname",
        ),
        date_posted_excel=Case(
            When(date_posted__isnull=True, then=Value("")),
            default=Func(
                'date_posted',
                function='TO_CHAR',
                template="TO_CHAR(%(expressions)s, 'DD-MM-YYYY')",
                output_field=CharField()
            )
        ),
        date_created_excel=Case(
            When(created_at__isnull=True, then=Value("")),
            default=Func(
                'created_at',
                function='TO_CHAR',
                template="TO_CHAR(%(expressions)s, 'DD-MM-YYYY HH12:MI AM')",
                output_field=CharField()
            )
        ),
        tag_names=Coalesce(
            StringAgg(
                "tags__name",
                delimiter=", ",
                distinct=True,
            ),
            Value("", output_field=CharField()),
            output_field=CharField(),
        ),
        linkedin_tag=Case(
            When(linkedin_tags__len__gt=0, then=Func(
                F("linkedin_tags"),
                function="jsonb_array_elements_text",
                template="(%(expressions)s->>0)",
                output_field=CharField(),
            )),
            default=Value(""),
            output_field=CharField(),
        ),
        employment_type=Case(
            When(job__employment_type__isnull=True, then=Value('')),
            default="job__employment_type__name",
            output_field=CharField(),
        ),
        department=Case(
            When(job__department__isnull=True, then=Value('')),
            default="job__department__name",
            output_field=CharField(),
        ),
        uid_str=Cast("uid", output_field=CharField())

    ).order_by("job", "-created_at").distinct().values_list("job_id",
                            "uid_str",
                             "role",
                            "date_created_excel",
                             "status",
                             "tag_names",
                             "linkedin_tag",
                             "employment_type",
                             "job__hiring_company_name",
                             "department",
                             "job__work_structure",
                             "country__name",
                             "province__name",
                             "city",
                             "postal_code",
                             "recruiter_name",
                             "applicants")
    current_job = None
    for job_post in job_posts:
        if current_job is not None and current_job != job_post[0]:
            rows.append(empty_header)
        rows.append([*job_post[1:], job_url(job_post[1]), "" ])


    return export_rows_to_excel(rows=rows, headers=headers, title=title, background=background)