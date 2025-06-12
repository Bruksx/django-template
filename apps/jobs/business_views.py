from typing import Literal, Optional, List
from uuid import UUID

from config.permissions import IsBusinessUser
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from helpers.utils import convert_base64_to_image_file
from monkeypatches.response import Response
from ninja import Router, PatchDict
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from accounts.models import Department, Role, SkillCategory, Skill
from accounts.schemas.talent import SkillSchema
from chats.schemas import ResponseSchema
from notification.notifications import send_talents_job_matching_notification
from paginations import CustomPageNumberPaginationExtra
from paginations import CustomPaginatedResponseSchema as PaginatedResponseSchema
from settings.models import WorkFlowStage
from . import schemas as job_schemas
from .enums import JobStatusType, PhaseType, QuestionTypeEnum, ActionType
from .models import (
    EmploymentType, BusinessModel, JobLevel, JobPost, Job, RequiredAttribute, JobApplication, AvailableDay,
    ScreeningQuestion, QuestionOption, Answer
)
from .schemas import (
    EmploymentTypeSchema, DepartmentSchema, RoleSchema, SkillCategorySchema, GenericNameAndUidSchema,
    JobLevelSchema, BulkJobPostSchema, JobDetailSchema, JobWorkflowViewPaginatedSchema,
    TalentListJobPostSchema
)
from .services import set_job_required_attributes, get_screening_questions_service

router = Router(tags=["Business Jobs"])
pagination_class = lambda page_size: CustomPageNumberPaginationExtra(page_size=page_size or 50)


@router.get("employment-types", response=list[EmploymentTypeSchema], tags=["Common"])
def get_employment_types(request, search=""):
    queryset = EmploymentType.objects.filter(parent=None)
    if search:
        queryset = queryset.filter(name__icontains=search)
    return queryset.distinct("name").order_by("name")


@router.get("departments", response=list[DepartmentSchema], tags=["Common"])
def get_departments(request, search=""):
    queryset = Department.objects.prefetch_related("industry").all()
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(industry__name__icontains=search))
    return queryset.distinct("name").order_by("name")


@router.get("roles", response=list[RoleSchema], tags=["Common"])
def get_roles(request, search=""):
    queryset = Role.objects.prefetch_related("department").all()
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
def get_skills_categories(request, search="", category=""):
    queryset = SkillCategory.objects.all().prefetch_related("skill_set")
    if search:
        queryset = queryset.filter(Q(name__icontains=search)|
                                   Q(skill__name__icontains=search)).distinct("uid")
    if category:
        queryset = queryset.filter(name__iexact=category)
    return Response(data=[SkillCategorySchema.from_orm(q, context={"search": search}) for q in queryset])


@router.get("skills", response={200: list[SkillSchema]}, tags=["Common"])
def get_skills(request, search="", category=""):
    queryset = Skill.objects.all()
    if search:
        queryset = queryset.filter(name__icontains=search)
    if category:
        queryset = queryset.filter(category__name__iexact=category)
    return queryset.distinct("name").order_by("name")


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
    if "status" in data:
        data["status"] = data["status"].value
        if data["status"] == JobStatusType.POSTED.value:
            data["posted_by"] = business_user
            data["date_posted"] = timezone.now()

    job_post.update(**data)
    return job_post

@router.patch("job-posts", response=ResponseSchema, auth=JWTAuth())
@transaction.atomic
def bulk_job_post_update(request, data: BulkJobPostSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_posts = JobPost.objects.filter(job__created_by__business=business_user.business, uid__in=data.job_posts)
    if data.action == ActionType.DELETE:
        job_ids = (JobApplication.objects.filter(job_post__in=job_posts).
                       only("job_post_id").values_list("job_post_id", flat=True))
        job_posts.exclude(id__in=job_ids).delete()
    else:
        job_posts.update(status=data.action.value)
    return Response({"message" : "actions have been applied successfully"}, status=200)

@router.post("{job_uid}/job-post", response=job_schemas.JobPostDetailSchema, auth=JWTAuth())
@transaction.atomic
def add_job_post(request, job_uid:UUID, data: job_schemas.MutateJobPostSchema):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job = Job.objects.filter(uid=job_uid, created_by=business_user).first()
    if not job:
        raise HttpError(404, "This job does not exist")
    request_data = data.dict()
    if "status" in request_data:
        request_data["status"] = request_data["status"].value
        if request_data["status"] == JobStatusType.POSTED.value:
            request_data["posted_by"] = business_user

    job_post = JobPost(
        **request_data,
        job=job
    )
    job_post.save()
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
def get_talents_by_job_post(request, job_post_uid: UUID, search: str=None):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    job_post = JobPost.objects.filter(uid=job_post_uid, job__created_by__business=business_user.business).first()
    if not job_post:
        raise HttpError(404, "Job Post not found")
    request.context = dict(job_post=job_post)
    query = Q()
    if search:
        query = (Q(user__first_name__icontains=search) |
                 Q(user__last_name__icontains=search)|
                 Q(user__email__icontains=search)
        )
    talents = job_post.get_talents()
    send_talents_job_matching_notification(talents.count(), job_post)
    return talents.filter(query).order_by("-user__last_login")

@router.post("", response=JobDetailSchema, auth=JWTAuth())
@transaction.atomic
def create_job(request, data:PatchDict[job_schemas.OptionalCreateJobSchema]):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
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

    if not data.get("hiring_company_name"):
        data["hiring_company_name"] = business.name
    if not data.get("hiring_company_description"):
        data["hiring_company_description"] = business.description
    if "work_structure" in data:
        data["work_structure"] = data["work_structure"].value
    if "lunch_break" in data:
        data["lunch_break"] = data["lunch_break"].value
    if "technological_requirement" in data:
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
    if data.get("logo"):
        data["logo"] = convert_base64_to_image_file(data["logo"])


    for job_post in job_posts:
        job_post["status"] = job_post["status"].value if job_post.get("status") else JobStatusType.DRAFT.value
        JobPost.objects.create(job=job, **job_post)
    for question in screening_questions:
        question["type"] = question["type"].value
        options = question.pop("options")
        question = ScreeningQuestion.objects.create(job=job, **question)
        QuestionOption.objects.bulk_create([QuestionOption(**option, question=question) for option in options])

    return job

@router.patch("{job_uid}", response=JobDetailSchema, auth=JWTAuth())
@transaction.atomic
def update_job(request, data:PatchDict[job_schemas.UpdateJobSchema], job_uid:UUID):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    business = business_user.business
    job = Job.objects.filter(uid=job_uid, created_by__business=business_user.business).first()
    if not job:
        raise HttpError(404, "Job not found")
    additional_languages = data.pop("additional_languages", list())
    skills = data.pop("skills", list())
    business_models = data.pop("business_models", list())
    required_attributes = data.pop("required_attributes", None)
    if not data.get("hiring_company_name"):
        data["hiring_company_name"] = business.name
    if not data.get("hiring_company_description"):
        data["hiring_company_description"] = business.description
    if "work_structure" in data:
        data["work_structure"] = data["work_structure"].value
    if "lunch_break" in data:
        data["lunch_break"] = data["lunch_break"].value
    if "technological_requirement" in data:
        data["technological_requirement"] = data["technological_requirement"].value
    job.update(**data)
    if "availability" in data:
        availability = data.pop("availability")
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
    if data.get("logo"):
        data["logo"] = convert_base64_to_image_file(data["logo"])
    if business_models:
        job.business_models.set(business_models)
    if skills:
        job.skills.set(skills)
    if additional_languages:
        job.additional_languages.set(additional_languages)
    job.save()
    if required_attributes:
        set_job_required_attributes(required_attributes, job)

    return job



@router.get("", response=JobWorkflowViewPaginatedSchema, auth=JWTAuth())
def job_list(request, page_size=50, page=1, search="", status:JobStatusType=None):
    IsBusinessUser.check(request)
    business_user = request.user.businessuser
    queryset = Job.objects.prefetch_related("jobpost_set").filter(created_by__business=business_user.business)
    if search:
        queryset = queryset.filter(Q(title__icontains=search)|
                                   Q(role__name__icontains=search)|
                                   Q(hiring_company_name=search))
    if status:
        queryset = queryset.filter(jobpost__status=status.value).distinct()

    pagination = pagination_class(page_size).Input(page=page, page_size=page_size)
    return pagination_class(page_size).paginate_queryset(
        queryset=queryset.order_by("-created_at"),
        request=request,
        pagination=pagination,
        roles=queryset.count(),
        posts=business_user.business.job_posts().filter(job__in=queryset).count()
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
                    new_application:bool=None,
                    sort_by:Optional[Literal["applicant", "location",
"match", "created_at", "stage", "phase", "experience"]]=None, asc:bool=True, search:str="", ):
    IsBusinessUser.check(request)
    business = request.user.businessuser.business
    queryset = JobApplication.objects.filter(job_post__uid=job_post_uid, recruiter__business=business,
                                             applicant__deleted_at__isnull=True)
    if search:
        queryset = queryset.filter(Q(
            Q(applicant__user__fullname__icontains=search)|
            Q(applicant__country__name__icontains=search)|
            Q(applicant__user__email__icontains=search)
        )).distinct()
    if phase:
        queryset = queryset.filter(stage__phase=phase.value)
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
            queryset = queryset.order_by(f"{sign}match")
        elif sort_by == "created_at":
            queryset = queryset.order_by(f"{sign}created_at")
        elif sort_by == "stage":
            queryset = queryset.order_by(f"{sign}stage__order")
        elif sort_by == "phase":
            queryset = queryset.order_by(f"{sign}stage__phase_order")
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
    application.update(**data.dict())
    return application


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
    if not _question:
        raise HttpError(404, "This question does not exist")

    if "type" in question:
        question["type"] = question["type"].value
        options = [job_schemas.QuestionOptionSchema.from_orm(option).dict() for option in _question.options()]
        if options and question["type"] in (QuestionTypeEnum.FILE.value, QuestionTypeEnum.TEXT.value):
            raise HttpError(400, "This question type does not support options")
        if question["type"] == QuestionTypeEnum.SINGLE_SELECT.value:
            correct_option = [option for option in options if option["is_accepted"]]
            if len(correct_option) != 1:
                raise HttpError(400, "Single select question must have exactly one correct option")
        if question["type"] == QuestionTypeEnum.MULTI_SELECT.value:
            correct_options = [option for option in options if option["is_accepted"]]
            if len(correct_options) < 2:
                raise HttpError(400, "Multiple select question must have at least two correct options")
    _question.update(**question)
    return _question

@router.post("screening-questions/{question_uid}/options", auth=JWTAuth(), tags=["Screening Test"],
             response=job_schemas.QuestionSchema)
@transaction.atomic
def mutate_options_in_screening_questions(request, question_uid:UUID, data: List[job_schemas.MutateOptionSchema]):
    IsBusinessUser.check(request)
    question = ScreeningQuestion.objects.filter(uid=question_uid,
                                                job__created_by__business=request.user.businessuser.business).first()
    if not question:
        raise HttpError(404, "This question does not exist")
    if question.type in (QuestionTypeEnum.FILE.value, QuestionTypeEnum.TEXT.value):
        raise HttpError(400, "This question type does not support options")
    question_options = question.options().all()
    new_options = [option for option in data if not option.uid]
    changing_options = [option for option in data if option.uid]
    changing_options_id = (option.uid for option in changing_options)
    existing_options = question_options.exclude(uid__in=changing_options_id)
    if question.type == QuestionTypeEnum.SINGLE_SELECT.value:
        new_correct_option = [option for option in new_options if option.is_accepted]
        changing_correct_option = [option for option in changing_options if option.is_accepted]
        correct_option = new_correct_option + changing_correct_option
        if (len(correct_option) + existing_options.filter(is_accepted=True).count()) != 1:
            raise HttpError(400, "Single select question must have exactly one correct option")
    if question.type == QuestionTypeEnum.MULTI_SELECT.value:
        new_correct_options = [option for option in new_options if option.is_accepted]
        changing_correct_options = [option for option in changing_options if option.is_accepted]
        correct_options = new_correct_options + changing_correct_options
        if (len(correct_options) + existing_options.filter(is_accepted=True).count()) < 2:
            raise HttpError(400, "Multiple select question must have at least two correct options")
    for option in data:
        if not option.uid:
            opt_data = option.dict()
            opt_data.pop("uid", None)
            QuestionOption.objects.create(question=question, **opt_data)
        else:
            question.questionoption_set.filter(uid=option.uid).update(**option.dict())
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


