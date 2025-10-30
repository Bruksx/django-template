import logging
from datetime import timedelta
from typing import Literal, Optional, List
from uuid import UUID

from django.db.models.functions import Concat

from config.permissions import IsBusinessUser
from django.db import transaction
from django.db.models import Q, Count, Exists, Subquery, OuterRef, Case, When, F, Value
from django.shortcuts import get_object_or_404
from django.utils import timezone

from helpers.email.jobs import send_indeed_apply_email
from helpers.utils import convert_base64_to_image_file, to_utc
from monkeypatches.response import Response
from monkeypatches.q_cluster import async_task
from ninja import Router, PatchDict, Query
from ninja.errors import HttpError
from ninja_extra import paginate
from ninja_jwt.authentication import JWTAuth

from accounts.models import Department, Role, SkillCategory, Skill, BusinessUser, Talent
from accounts.schemas.talent import SkillSchema
from chats.schemas import ResponseSchema
from notification.notifications import send_talents_job_matching_notification
from paginations import CustomPageNumberPaginationExtra, CustomPaginatedResponseSchema
from paginations import CustomPageNumberPaginationExtra as PageNumberPaginationExtra
from paginations import CustomPaginatedResponseSchema as PaginatedResponseSchema

from settings.models import WorkFlowStage

from services.job_posting.schema.indeed import ScreenerQuestions, WidgetScreenerSchema
from services.job_posting.services.indeed import get_basic_screening_questions
from . import schemas as job_schemas
from .enums import JobStatusType, PhaseType, QuestionTypeEnum, ActionType
from .models import (
    EmploymentType, BusinessModel, JobLevel, JobPost, Job, RequiredAttribute, JobApplication, AvailableDay,
    ScreeningQuestion, QuestionOption, Answer, JobInvite
)
from .schemas import (
    EmploymentTypeSchema, DepartmentSchema, RoleSchema, SkillCategorySchema, GenericNameAndUidSchema,
    JobLevelSchema, BulkJobPostSchema, JobDetailSchema, JobWorkflowViewPaginatedSchema,
    TalentListJobPostSchema, JobLogoSchema, MutateOptionSchema, BusinessJobFilterQuerySchema, TalentJobPostListSchema,
    TalentJobFilterQuerySchema, EmploymentParentTypeSchema, TalentListJobPostSchema2, IndeedApplySchema
)
from .queries import add_application_match_score, add_job_post_annotations
from .services import set_job_required_attributes, get_screening_questions_service, update_job_post_service, \
    update_bulk__job_posts_service, send_email_on_stage_update, create_job_post_service, \
    bulk_job_posts_service, validate_screening_questions, update_screening_question_options, \
    get_talents_by_job_posts_service

router = Router(tags=["Business Jobs"])
pagination_class = lambda page_size: CustomPageNumberPaginationExtra(page_size=page_size or 50)


@router.get("employment-types", response=list[EmploymentParentTypeSchema], tags=["Common"])
def get_employment_types(request, search=""):
    queryset = EmploymentType.objects.filter(parent=None)
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.distinct("name").order_by("name")


@router.get("departments", response=list[DepartmentSchema], tags=["Common"])
def get_departments(request, search="", role:Optional[UUID]=None):
    queryset = Department.objects.prefetch_related("industry").all()
    if role:
        queryset = queryset.filter(role__uid=role)
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(industry__name__icontains=search))
    return queryset.distinct("name").order_by("name")


@router.get("roles", response=list[RoleSchema], tags=["Common"])
def get_roles(request, search="", department:Optional[UUID]=None):
    queryset = Role.objects.prefetch_related("department").annotate(
        duplicated=Exists(
            Role.objects.filter(
                name__iexact=OuterRef("name"),
            ).exclude(id=OuterRef("id"))
        )
    ).annotate(
        fullname=Case(
            When(duplicated=False, then=F("name")),
            default=Concat(F("name"), Value(' ('),  F("department__name"),  Value(')')),
        )
    ).all()

    if department:
        queryset = queryset.filter(department__uid=department)
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(department__name__icontains=search))
    return queryset.order_by("fullname")


@router.get("business-roles", auth=JWTAuth(), response=list[RoleSchema], tags=["Common"])
def get_business_roles(request, search=""):
    IsBusinessUser.check(request)
    business = request.user.businessuser.business
    role_ids = Job.objects.select_related("created_by__business").filter(created_by__business=business).only("role_id").distinct("role_id").values_list("role_id", flat=True)
    queryset = Role.objects.prefetch_related("department").filter(id__in=role_ids)
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(department__name__icontains=search))
    return queryset.distinct("name").order_by("name")

@router.get("job-levels", response=list[JobLevelSchema], tags=["Common"])
def get_job_levels(request, search=""):
    queryset = JobLevel.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.distinct("name").order_by("name")

@router.get("skill-categories", response={200: list[SkillCategorySchema]}, tags=["Common"])
def get_skills_categories(request, search="", category="", department:Optional[UUID]=None):
    queryset = SkillCategory.objects.all().prefetch_related("skill_set")
    if department:
        queryset = queryset.filter(skill__department__uid=department).distinct("skill__category_id")

    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(skill__name__icontains=search)).distinct("uid")
    if category:
        queryset = queryset.filter(name__iexact=category)
    return Response(data=[SkillCategorySchema.from_orm(q, context={"search": search, "department": department}) for q in queryset])


@router.get("skills", response={200: list[SkillSchema]}, tags=["Common"])
def get_skills(request, search="", category="", department:UUID=None):
    queryset = Skill.objects.annotate(
        duplicated=Exists(
            Skill.objects.filter(
                name__iexact=OuterRef("name"),
            ).exclude(id=OuterRef("id"))
        )
    ).annotate(
        fullname=Case(
            When(duplicated=False, then=F("name")),
            default=Concat(F("name"), Value(' ('),  F("department__name"),  Value(')')),
        )
    )
    if search:
        queryset = queryset.filter(name__icontains=search)
    if department:
        queryset = queryset.filter(department__uid=department)
    if category:
        queryset = queryset.filter(category__name__iexact=category)
    return queryset.order_by("name")


@router.get("business-models", response=list[GenericNameAndUidSchema], tags=["Common"])
def get_business_models(request, search=""):
    queryset = BusinessModel.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.distinct("name").order_by("name")


@router.patch("{job_uid}/required-attributes", response=job_schemas.RequiredAttributeSchema, auth=JWTAuth())
@transaction.atomic
def set_required_attributes(request, data:job_schemas.MutateRequiredAttributeSchema, job_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job = Job.objects.filter(created_by__business=business_user.business, uid=job_uid).first()
    if not job:
        raise HttpError(404, "Job not found")
    request_data = data.dict()
    return set_job_required_attributes(request_data, job)


@router.get("{job_uid}/required-attributes", response=job_schemas.RequiredAttributeSchema, auth=JWTAuth())
def get_required_attributes(request, job_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job = Job.objects.filter(created_by__business=business_user.business, uid=job_uid).first()
    if not job:
        raise HttpError(404, "Job not found")
    required_attributes, _ = RequiredAttribute.objects.get_or_create(job=job)
    return required_attributes


@router.delete("job-post/{job_post_uid}", auth=JWTAuth())
def delete_job_post(request, job_post_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_post =  JobPost.objects.filter(uid=job_post_uid, job__created_by__business=business_user.business).first()
    if not job_post:
        raise HttpError(404, "This job post does not exist")
    if job_post.jobapplication_set.count() > 0:
        raise HttpError(400, "Some job applications are tied to this job post")
    job_post.delete()
    return Response(status=204, data={"message": "Job post deleted"})


@router.post("job-post/{job_post_uid}/refresh", auth=JWTAuth())
def refresh_job_post(request, job_post_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_post =  JobPost.objects.filter(uid=job_post_uid, job__created_by__business=business_user.business).first()
    if not job_post:
        raise HttpError(404, "This job post does not exist")
    now = timezone.now()
    if job_post.last_refreshed:
        if (now - job_post.last_refreshed) < timedelta(days=14):
            raise HttpError(400, "You can only refresh job posts older than 2 weeks")
    else:
        if (now - job_post.date_posted) < timedelta(days=14):
            raise HttpError(400, "You can only refresh job posts older than 2 weeks")
    job_post.update(last_refreshed=timezone.now())
    return Response(status=200, data={"message": "Job post refreshed successfully"})

@router.post("job/{job_uid}/refresh", auth=JWTAuth())
def refresh_job(request, job_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    JobPost.objects.filter(job__uid=job_uid, job__created_by__business=business_user.business).exclude(
        last_refreshed__gte=(timezone.now() - timedelta(days=14))).update(
            last_refreshed=timezone.now()
        )
    return Response(status=200, data={"message": "Job refreshed successfully"})



@router.delete("job/{job_uid}", auth=JWTAuth())
def delete_job(request, job_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job =  Job.objects.filter(uid=job_uid, created_by__business=business_user.business).first()
    if not job:
        raise HttpError(404, "This job does not exist")
    if JobApplication.objects.filter(job_post__job=job).exists():
        raise HttpError(400, "Some job applications are tied to this job")
    job.delete()
    return Response(status=204, data={"message": "Job deleted"})

@router.patch("job-post/{job_post_uid}", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
@transaction.atomic
def update_job_post(request, job_post_uid, data: PatchDict[job_schemas.MutateJobPostSchema]):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_post =  JobPost.objects.filter(uid=job_post_uid, job__created_by__business=business_user.business).first()
    if not job_post:
        raise HttpError(404, "This job post does not exist")
    status = data.get("status")
    return update_job_post_service(job_post, business_user, data, status=status.value if status else None)

@router.patch("job-posts", response=ResponseSchema, auth=JWTAuth())
@transaction.atomic
def bulk_job_post_update(request, data: BulkJobPostSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    if data.action == ActionType.DELETE:
        job_ids = (JobApplication.objects.filter(job_post__uid__in=data.job_posts).
                       only("job_post_id").values_list("job_post_id", flat=True))
        JobPost.objects.filter(job__created_by__business=business_user.business, uid__in=data.job_posts).exclude(id__in=job_ids).delete()
    else:
        async_task(update_bulk__job_posts_service, business_user, data.job_posts, data.action)
    return Response({"message" : "actions have been applied successfully"}, status=200)

@router.post("{job_uid}/job-post", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
@transaction.atomic
def add_job_post(request, job_uid:UUID, data: job_schemas.MutateJobPostSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job = Job.objects.filter(uid=job_uid, created_by=business_user).first()
    if not job:
        raise HttpError(404, "This job does not exist")

    job_post = create_job_post_service(business_user, job, [data.dict()])
    return job_post


@router.get("job-posts/{job_post_uid}", response=job_schemas.JobPostFullDetailSchema, auth=JWTAuth())
@transaction.atomic
def get_job_post_detail(request, job_post_uid):
    query = dict(uid=job_post_uid)
    if hasattr(request.user, "businessuser"):
        query["job__created_by__business"] = request.user.businessuser.business
    if hasattr(request.user, "talent"):
        request.context = dict(talent=request.user.talent)
    job_post = JobPost.objects.filter(**query).first()
    if not job_post:
        raise HttpError(404, "Job Post not found")
    return job_post

@router.get("job-posts/{job_post_uid}/talents", response=list[TalentListJobPostSchema], auth=JWTAuth())
def get_talent_list_by_job_post(request, job_post_uid: UUID, search: str=None):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_post = JobPost.objects.filter(uid=job_post_uid, job__created_by__business=business_user.business).first()
    return get_talents_by_job_posts_service(request, job_post, search)


@router.get("job-posts/{job_post_uid}/paginated-talents", response=CustomPaginatedResponseSchema[TalentListJobPostSchema2], auth=JWTAuth())
@paginate(CustomPageNumberPaginationExtra, page_size=50)
def get_talents_by_job_post(request, job_post_uid: UUID, search: str=None):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_post = JobPost.objects.filter(uid=job_post_uid, job__created_by__business=business_user.business).first()
    return get_talents_by_job_posts_service(request, job_post, search)

@router.post("", response=JobDetailSchema, auth=JWTAuth())
@transaction.atomic
def create_job(request, data:PatchDict[job_schemas.OptionalCreateJobSchema]):
    IsBusinessUser.check(request)
    business_user: BusinessUser = request.user.businessuser
    business = business_user.business
    if WorkFlowStage.objects.filter(created_by__business=business).values_list("phase", flat=True).distinct("phase").count() != len(PhaseType.values()):
        raise HttpError(400, "You must have a workflow stage for each phase")
    data["created_by"] = business_user
    availability = data.pop("availability", list())
    screening_questions = data.pop("screening_questions", list())
    required_attributes = data.pop("required_attributes", None)
    job_posts = data.pop("job_posts", list())
    additional_languages = data.pop("additional_languages", list())
    skills = data.pop("skills", list())
    business_models = data.pop("business_models", list())
    logo = data.pop("logo", None)

    if logo:
        logo_data = JobLogoSchema(**logo)
        name = logo_data.get_name()
        data["logo"] = convert_base64_to_image_file(logo_data.base64, name)


    if not data.get("hiring_company_name"):
        data["hiring_company_name"] = business.name
    if not data.get("hiring_company_description"):
        data["hiring_company_description"] = business.description
    if data.get("work_structure"):
        data["work_structure"] = data["work_structure"].value
    if data.get("lunch_break"):
        data["lunch_break"] = data["lunch_break"].value
    if data.get("technological_requirement"):
        data["technological_requirement"] = data["technological_requirement"].value


    job = Job.objects.create(**data)
    job.business_models.set(business_models)
    job.skills.set(skills)
    job.additional_languages.set(additional_languages)
    job.save()

    if required_attributes:
        set_job_required_attributes(required_attributes, job)

    for available_day in availability:
        available_day["day"] = available_day["day"].value
        uid =  available_day.pop("uid", None)
        active = available_day.pop("active", True)
        if uid and not active:
            job.availableday_set.filter(uid=uid).delete()
        elif uid and active:
            job.availableday_set.filter(uid=uid).update(**available_day)
        elif not uid:
            day = available_day['day']
            if job.availableday_set.filter(day=day).exists():
                raise HttpError(400, f"{day} already exists")
            AvailableDay.objects.create(**available_day, job=job)

    create_job_post_service(business_user, job, job_posts)
    for question in screening_questions:
        question["type"] = question["type"].value
        options = question.pop("options")
        question = ScreeningQuestion.objects.create(job=job, **question)
        options_data = [MutateOptionSchema(**o) for o in options]
        _, error = update_screening_question_options(question, options_data)
        if error:
            logging.critical(error, exc_info=True)
            raise error

    return job

@router.patch("{job_uid}", response=JobDetailSchema, auth=JWTAuth())
@transaction.atomic
def update_job(request, data:PatchDict[job_schemas.UpdateJobSchema], job_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    business = business_user.business
    screening_questions = data.pop("screening_questions", list())
    job = Job.objects.filter(uid=job_uid, created_by__business=business_user.business).first()
    if not job:
        raise HttpError(404, "Job not found")
    additional_languages = data.pop("additional_languages", list())
    skills = data.pop("skills", list())
    business_models = data.pop("business_models", list())
    required_attributes = data.pop("required_attributes", None)
    job_posts = data.pop("job_posts", list())
    availability = data.pop("availability", list())
    logo = data.pop("logo", None)
    if not data.get("hiring_company_name"):
        data["hiring_company_name"] = business.name
    if not data.get("hiring_company_description"):
        data["hiring_company_description"] = business.description
    if data.get("work_structure"):
        data["work_structure"] = data["work_structure"].value
    if data.get("lunch_break"):
        data["lunch_break"] = data["lunch_break"].value
    if data.get("technological_requirement"):
        data["technological_requirement"] = data["technological_requirement"].value

    if logo:
        logo_data = JobLogoSchema(**logo)
        name = logo_data.get_name()
        logging.critical(f"name:  {name}")
        data["logo"] = convert_base64_to_image_file(logo_data.base64, name)

    job.update(**data)
    for available_day in availability:
        available_day["day"] = available_day["day"].value
        uid =  available_day.pop("uid", None)
        active = available_day.pop("active", True)
        if uid and not active:
            job.availableday_set.filter(uid=uid).delete()
        elif uid and active:
            job.availableday_set.filter(uid=uid).update(**available_day)
        elif not uid:
            day = available_day['day']
            if job.availableday_set.filter(day=day).exists():
                raise HttpError(400, f"{day} already exists")
            AvailableDay.objects.create(**available_day, job=job)

    if business_models:
        job.business_models.set(business_models)
    if skills:
        job.skills.set(skills)
    if additional_languages:
        job.additional_languages.set(additional_languages)
    job.save()
    if required_attributes:
        set_job_required_attributes(required_attributes, job)

    if len(job_posts) == 1:
        if "uid" in job_posts[0]:
            job_post = JobPost.objects.filter(uid=job_posts[0]["uid"]).first()
            if not job_post:
                raise HttpError(404, "Job post not found")
            update_job_post_service(job_post, business_user, data=job_posts[0], raise_error=True)
        else:
            create_job_post_service(job, business_user, job_posts)
    else:
        bulk_job_posts_service(job,  job_posts, business_user)

    if screening_questions:
        new_questions = (q for q in screening_questions if not q.get("uid"))
        old_questions = (q for q in screening_questions if q.get("uid"))

        for question in new_questions:
            question["type"] = question["type"].value
            options = question.pop("options")
            question = ScreeningQuestion.objects.create(job=job, **question)
            options_data = [MutateOptionSchema(**o) for o in options]
            _, error = update_screening_question_options(question, options_data)
            if error:
                logging.critical(error, exc_info=True)
                raise error

        for question_data in old_questions:
            question = ScreeningQuestion.objects.filter(uid=question_data.get("uid")).first()
            if "type" in question_data:
                question_data["type"] = question_data["type"].value
            question = question.update(**question_data)
            options_data = [MutateOptionSchema(**o) for o in question_data["options"]]
            _, error = update_screening_question_options(question, options_data)
            if error:
                logging.critical(error, exc_info=True)
                raise error
    return job



@router.get("", response=JobWorkflowViewPaginatedSchema, auth=JWTAuth())
def job_list(request, page_size=50, page=1, filters: BusinessJobFilterQuerySchema = Query(...)
             ):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    context = dict(business=business_user.business)
    queryset = Job.objects.prefetch_related("jobpost_set").annotate(jobpost_count=Count('jobpost')).filter(created_by__business=business_user.business,
                                                                                                           jobpost_count__gt=0)
    filters = filters.convert_to_schema()
    context = filters.get_context(context=context)
    request.context = context
    queryset = filters.get_queryset(queryset=queryset)

    pagination = pagination_class(page_size).Input(page=page, page_size=page_size)
    return pagination_class(page_size).paginate_queryset(
        queryset=queryset.order_by("-created_at"),
        request=request,
        pagination=pagination,
        roles=queryset.count(),
        posts= filters.filter_job_posts(context, business_user.business.job_posts()).filter(job__in=queryset).count()
    )


@router.get("{job_uid}", response=job_schemas.FullJobDetailSchema, auth=JWTAuth())
def job_detail(request, job_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job = Job.objects.prefetch_related("jobpost_set").filter(created_by__business=business_user.business, uid=job_uid).first()
    if not job:
        raise HttpError(404, "This job does not exist")
    return job


@router.get("job-posts/{job_post_uid}/applications", response=PaginatedResponseSchema[job_schemas.JobApplicationListSchema], auth=JWTAuth())
def view_applicants(request, job_post_uid:UUID, page_size=50, page=1, phase:Optional[PhaseType]=None,
                    stage: Optional[UUID]=None,
                    new_application:bool=None,
                    sort_by:Optional[Literal["applicant", "location",
"match", "created_at", "stage", "phase", "experience", "invited"]]=None, asc:bool=True, search:str="", invited:Optional[bool]=None):
    IsBusinessUser.check(request)
    business = request.user.businessuser.business
    job_post = get_object_or_404(JobPost, uid=job_post_uid)
    queryset = JobApplication.objects.select_related("stage", "applicant", "applicant__user",
                                                     "applicant__country").annotate(invited=Exists(Subquery(JobInvite.objects.filter(
            job=OuterRef('job_post__job'), talent=OuterRef('applicant')
        )))).filter(job_post=job_post, stage__created_by__business=business,
                                         applicant__deleted_at__isnull=True)
    queryset = add_application_match_score(queryset, job_post)
    if search:
        q = Q()
        for s in search.split(" "):
            if s:
                q = q | Q(applicant__user__fullname__icontains=s) | Q(applicant__user__email__icontains=s) | Q(applicant__country__name__icontains=s)

        queryset = queryset.filter(q).distinct()
    if phase:
        queryset = queryset.filter(stage__phase=phase.value)
    if stage:
        queryset = queryset.filter(stage__uid=stage)
    if invited:
        queryset = queryset.filter(invited=invited)

    if new_application is not None:
        if new_application is True:
            queryset = queryset.filter(Q(stage__isnull=True)| Q(stage__phase=PhaseType.NEW.value))
        else:
            queryset = queryset.filter(Q(stage__isnull=False) & ~Q(stage__phase=PhaseType.NEW.value))
    if sort_by:
        sign = "-" if asc is False else ""
        if sort_by == "applicant":
            queryset = queryset.order_by(f"{sign}applicant__user__fullname")
        elif sort_by == "location":
            queryset = queryset.order_by(f"{sign}applicant__country__name")
        elif sort_by == "match":
            queryset = queryset.annotate(
                match=Case(
                    When(computed_match_score__isnull=False, then=F("computed_match_score")), default=float(0)
                )
            ).order_by(f"{sign}match")
        elif sort_by == "created_at":
            queryset = queryset.order_by(f"{sign}created_at")
        elif sort_by == "stage":
            queryset = queryset.order_by(f"{sign}stage__order")
        elif sort_by == "phase":
            queryset = queryset.order_by(f"{sign}stage__phase_order")
        elif sort_by == "invited":
            queryset = queryset.order_by(f"{sign}invited")
    pagination = pagination_class(page_size).Input(page=page, page_size=page_size)
    return pagination_class(page_size).paginate_queryset(
        queryset=queryset,
        request=request,
        pagination=pagination
    )

@router.patch("job-posts/applications/{application_uid}", response=job_schemas.JobApplicationListSchema, auth=JWTAuth())
@transaction.atomic
def update_application(request, application_uid:UUID, data:job_schemas.UpdateApplicationSchema):
    IsBusinessUser.check(request)
    application = JobApplication.objects.filter(uid=application_uid, recruiter__business=request.user.businessuser.business).first()
    if not application:
        raise HttpError(404, "This application does not exist")
    previous_stage = application.stage
    application.update(**data.dict())
    send_email_on_stage_update(application=application, previous_stage=previous_stage, business_user=request.user.businessuser)
    return application


@router.patch("job-posts/applications/bulk/update", response=List[job_schemas.JobApplicationListSchema], auth=JWTAuth())
@transaction.atomic
def bulk_update_application(request, data:job_schemas.BulkUpdateApplicationSchema):
    IsBusinessUser.check(request)
    applications = JobApplication.objects.filter(uid__in=data.uids, recruiter__business=request.user.businessuser.business).iterator()
    for application in applications:
        previous_stage = application.stage
        application.update(stage=data.stage)
        async_task(send_email_on_stage_update, application=application, previous_stage=previous_stage, business_user=request.user.businessuser)
    return JobApplication.objects.filter(uid__in=data.uids)


@router.post("{job_uid}/screening-questions", response=job_schemas.QuestionSchema, auth=JWTAuth(),
            tags=["Screening Test"])
@transaction.atomic
def add_screening_question(request, job_uid:UUID, data: job_schemas.CreateQuestionSchema):
    IsBusinessUser.check(request)
    job = Job.objects.filter(created_by__business=request.user.businessuser.business, uid=job_uid).first()
    if not job:
        raise HttpError(404, "This job does not exist")
    question = data.dict()
    question["type"] = question["type"].value
    options = question.pop("options", None)
    if options and question["type"]  in (QuestionTypeEnum.FILE.value, QuestionTypeEnum.TEXT.value):
        raise HttpError(400, "This question type does not support options")
    if question["type"] == QuestionTypeEnum.TEXT.value and not question.get("text"):
        raise HttpError(400, "Text question must have a text")
    if question["type"] == QuestionTypeEnum.FILE.value and not question.get("file"):
        raise HttpError(400, "File question must have a file")
    if question["type"] == QuestionTypeEnum.SINGLE_SELECT.value:
        correct_option = [option for option in options if option["is_accepted"]]
        if len(correct_option) != 1:
            raise HttpError(400, "Single select question must have exactly one correct option")
    if question["type"] == QuestionTypeEnum.MULTI_SELECT.value:
        correct_options = [option for option in options if option["is_accepted"]]
        if len(correct_options) < 2:
            raise HttpError(400, "Multiple select question must have at least two correct options")
    question = ScreeningQuestion.objects.create(job=job, **question)
    QuestionOption.objects.bulk_create([QuestionOption(**option, question=question) for option in options])
    return question

@router.patch("screening-questions/{question_uid}", auth=JWTAuth(), tags=["Screening Test"],
              response=job_schemas.QuestionSchema)
@transaction.atomic
def update_screening_question(request, question_uid:UUID, question: PatchDict[job_schemas.UpdateQuestionSchema]):
    IsBusinessUser.check(request)
    _question = ScreeningQuestion.objects.filter(uid=question_uid,
            job__created_by__business=request.user.businessuser.business).first()
    _, error = validate_screening_questions(_question, question)
    if error:
        raise error
    if "type" in question:
        question["type"] = question["type"].value
    _question.update(**question)
    return _question

@router.post("screening-questions/{question_uid}/options", auth=JWTAuth(), tags=["Screening Test"],
             response=job_schemas.QuestionSchema)
@transaction.atomic
def mutate_options_in_screening_questions(request, question_uid:UUID, data: List[job_schemas.MutateOptionSchema]):
    IsBusinessUser.check(request)
    question = ScreeningQuestion.objects.filter(uid=question_uid,
                                                job__created_by__business=request.user.businessuser.business).first()

    question, error = update_screening_question_options(question, data)
    if error:
        raise error
    return question

@router.delete("screening-questions/{question_uid}/options", auth=JWTAuth(), tags=["Screening Test"],
               response=job_schemas.QuestionSchema)
@transaction.atomic
def delete_options_from_screening_questions(request, question_uid: UUID, data: List[UUID]):
    IsBusinessUser.check(request)
    question = ScreeningQuestion.objects.filter(uid=question_uid,
                                                job__created_by__business=request.user.businessuser.business).first()
    if not question:
        raise HttpError(404, "This question does not exist")
    if question.type in (QuestionTypeEnum.FILE.value, QuestionTypeEnum.TEXT.value):
        raise HttpError(400, "This question type does not support options")
    if question.type == QuestionTypeEnum.SINGLE_SELECT.value:
        if question.options().filter(uid__in=data, is_accepted=True).exists():
            raise HttpError(400, "Single select question must have exactly one correct option")
    if question.type == QuestionTypeEnum.MULTI_SELECT.value:
        if question.options().exclude(uid__in=data).filter(is_accepted=True).count() < 2:
            raise HttpError(400, "Multiple select question must have at least two correct options")
    if len(data) == 0:
        raise HttpError(400, "No options to delete")
    question.questionoption_set.filter(uid__in=data).delete()
    return question


@router.delete("screening-questions/{question_uid}", auth=JWTAuth(), tags=["Screening Test"])
@transaction.atomic
def delete_screening_question(request, question_uid:UUID):
    IsBusinessUser.check(request)
    question = ScreeningQuestion.objects.filter(uid=question_uid,
            job__created_by__business=request.user.businessuser.business).first()
    if not question:
        raise HttpError(404, "This question does not exist")
    question.questionoption_set.all().delete()
    question.delete()
    return Response(status=204 ,data=None)

@router.get("{job_uid}/screening-questions", response=List[job_schemas.QuestionSchema], auth=JWTAuth(),
            tags=["Screening Test"])
def get_screening_questions(request, job_uid: UUID):
    IsBusinessUser.check(request)
    return get_screening_questions_service(request, job_uid)

@router.get("{job_uid}/indeed/screener-questions",tags=["Screening Test"])
def get_indeed_screening_questions(request, job_uid: UUID):
    from services.job_posting.services.indeed import screening_question_to_indeed_screener_questions
    job = Job.objects.filter(uid=job_uid).first()
    if not job:
        raise HttpError(404, "This job does not exist")
    return screening_question_to_indeed_screener_questions(job)



@router.get("applications/{application_uid}/screening-answers", response=List[job_schemas.ScreeningAnswerSchema], auth=JWTAuth(),
            tags=["Screening Test"])
def get_screening_answers(request, application_uid:UUID):
    IsBusinessUser.check(request)
    application = JobApplication.objects.filter(uid=application_uid, recruiter__business=request.user.businessuser.business).first()
    if not application:
        raise HttpError(404, "This application does not exist")
    return Answer.objects.filter(application=application)


@router.get("talents/{talent_uid}/job-posts", auth=JWTAuth(), response=PaginatedResponseSchema[TalentJobPostListSchema])
@paginate(PageNumberPaginationExtra, page_size=50)
def job_posts_for_talent(request, talent_uid:UUID, filters:TalentJobFilterQuerySchema = Query(...)):
    filters = filters.convert_to_schema()
    IsBusinessUser.check(request)
    talent: Talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "This talent does not exist")
    request.context = {"talent": talent}
    queryset = JobPost.objects.select_related("job", "country", "job__role", "job__created_by__business").filter(status=JobStatusType.POSTED.value)
    queryset = add_job_post_annotations(queryset, talent)
    return filters.get_queryset(talent=talent, queryset=queryset)


@router.get("indeed/apply-questions", response=WidgetScreenerSchema,
            summary="Get indeed screening questions for job applications",
            tags=["ATS"])
def get_indeed_screening_questions2(request, *args, **kwargs):
    return get_basic_screening_questions().dict()

@router.post("indeed/jobs/{job_post_uid}/apply", tags=['ATS'])
def handle_indeed_application(request, job_post_uid:UUID, data: IndeedApplySchema):
    job_post = JobPost.objects.filter(uid=job_post_uid).first()
    if job_post:
        async_task(send_indeed_apply_email, job_post, data.email, data.firstName, data.lastName)
    return Response(status=200, data=dict(message="Application is successful"))