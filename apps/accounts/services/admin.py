from collections.abc import Iterable
from datetime import date, datetime
from datetime import timedelta
from math import ceil
from typing import Optional, Literal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Exists, OuterRef, F, Case, When, Value, CharField, Count, Subquery, IntegerField, Avg, \
    FloatField, \
    Func, Q
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from helpers.email.auth import send_admin_created_account_email
from monkeypatches.q_cluster import async_task
from ninja.errors import HttpError

from accounts.enums import BusinessUserRoleType, BusinessUserStatusType, UserType
from accounts.models import Business, BusinessUser, User, Talent, BusinessIndustry, Country, BusinessClient, \
    BannedAccount
from accounts.queries import add_profile_completion_annotation
from core.models import PageMetric, APIMetric
from jobs.enums import PhaseType, JobStatusType, WithdrawalFeedbackType
from jobs.models import JobPost, JobApplication, JobApplicationWithdrawal, JobPostMetrics, Job, JobPostTag, JobAlert
from . import talent as talent_services


def get_admin_business_metrics_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None,
    company: Optional[UUID] = None
):
    queryset = JobPost.objects.all()

    if company:
        queryset = queryset.filter(job__created_by__business_id=company)

    if role:
        queryset = queryset.filter(job__role__uid=role)

    if client:
        queryset = queryset.filter(job__hiring_company_name__iexact=client)

    if start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])
    elif start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    elif end_date:
        queryset = queryset.filter(created_at__lte=end_date)

    total_open_jobs = queryset.filter(status=JobStatusType.POSTED.value).count()

    application_query = JobApplication.objects.filter(job_post__in=queryset)
    total_applications = application_query.count()
    metrics = JobPostMetrics.objects.filter(job_post__in=queryset).aggregate(
        total_shares=Sum('daily_email_shares'),
        total_views=Sum('weekly_views')
    )
    total_job_shares = metrics["total_shares"] or 0
    total_job_views = metrics["total_views"] or 0


    total_interview_invitations = application_query.exclude(
        stage__phase__in=[PhaseType.NEW.value, PhaseType.REJECTED.value]
    ).values("applicant").distinct().count()

    business_ids = queryset.filter(status=JobStatusType.POSTED.value).annotate(
        business_id=F("job__created_by__business_id")
    ).values("business_id").distinct().values_list("business_id", flat=True)

    active_clients = BusinessClient.objects.filter(
        business_id__in=business_ids
    ).count()

    active_users_last_7_days = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=7)
    ).count()

    active_users_daily_average = int(active_users_last_7_days / 7) if active_users_last_7_days > 0 else 0
    job_phases = [
        {
            "phase": "Applications",
            "count": application_query.count(),
            "percentage_diff": 100
        }
    ]
    prev_count = 0
    for phase in PhaseType.values():
        count = application_query.filter(stage__phase=phase).count()
        job_phases.append({
            "phase": phase,
            "count": count,
            "percentage_diff": int(((count - prev_count) / prev_count) * 100) if prev_count > 0 else 100
        })
        prev_count = count

    return {
        "total_open_jobs": total_open_jobs,
        "total_applications": total_applications,
        "total_job_shares": total_job_shares,
        "total_job_views": total_job_views,
        "total_interview_invitations": total_interview_invitations,
        "active_clients": active_clients,
        "active_users_daily_average": active_users_daily_average,
        "active_users_last_7_days": active_users_last_7_days,
        "job_phases": job_phases
    }

def get_talent_metrics_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None,
    company: Optional[UUID] = None
):
    talent_query = Talent.objects.all()
    if start_date and end_date:
        talent_query = talent_query.filter(created_at__range=[start_date, end_date])
    elif start_date:
        talent_query = talent_query.filter(created_at__gte=start_date)
    elif end_date:
        talent_query = talent_query.filter(created_at__lte=end_date)

    if role:
        talent_query = talent_query.filter(role__uid=role)

    total_talent_signups = talent_query.count()

    application_query = JobApplication.objects.all()

    if start_date and end_date:
        application_query = application_query.filter(created_at__range=[start_date, end_date])
    elif start_date:
        application_query = application_query.filter(created_at__gte=start_date)
    elif end_date:
        application_query = application_query.filter(created_at__lte=end_date)

    total_applications = application_query.count()

    active_talents = Talent.objects.filter(visible=True).count()

    one_week_ago = timezone.now() - timedelta(days=7)
    talent_query = add_profile_completion_annotation(talent_query).filter(
        created_at__gte=one_week_ago
    )
    complete_week = talent_query.filter(complete_profile=True).count()
    semi_complete_week = talent_query.filter(semi_complete_profile=True).count()
    incomplete_week = talent_query.filter(complete_profile=False).count()

    profile_completion_this_week = {
        "complete": complete_week,
        "semi_complete": semi_complete_week,
        "incomplete": incomplete_week
    }

    withdrawal_query = JobApplicationWithdrawal.objects.all()
    if start_date and end_date:
        withdrawal_query = withdrawal_query.filter(created_at__range=[start_date, end_date])
    elif start_date:
        withdrawal_query = withdrawal_query.filter(created_at__gte=start_date)
    elif end_date:
        withdrawal_query = withdrawal_query.filter(created_at__lte=end_date)

    total_withdrawals = withdrawal_query.count()

    from jobs.enums import WithdrawalFeedbackType
    withdrawal_reasons = []
    for reason in WithdrawalFeedbackType:
        feedback_type = JobApplicationWithdrawal.feedback_type_to_number(reason)
        count = withdrawal_query.filter(feedback_type=feedback_type).count()
        withdrawal_reasons.append({
            "reason": reason.value,
            "count": count
        })

    return {
        "total_talent_signups": total_talent_signups,
        "total_applications": total_applications,
        "active_talents": active_talents,
        "profile_completion_this_week": profile_completion_this_week,
        "withdrawal_reasons": withdrawal_reasons,
        "total_withdrawals": total_withdrawals
    }


def get_businesses_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None,
    company: Optional[UUID] = None
):
    queryset = Business.objects.all().select_related("industry", "country", "created_by")

    if start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])
    elif start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    elif end_date:
        queryset = queryset.filter(created_at__lte=end_date)
    if client:
        queryset = queryset.filter(clients__name__iexact=client)
    if company:
        queryset = queryset.filter(created_by__uid=company)

    return queryset


def add_business_data(**kwargs):

    industry_uid = kwargs.pop("industry", None)
    country_uid = kwargs.pop("country", None)
    industry = None
    country = None
    if industry_uid:
        industry = BusinessIndustry.objects.filter(uid=industry_uid).first()
    if country_uid:
        country = Country.objects.filter(uid=country_uid).first()

    business = Business.objects.create(
        **kwargs,
        industry=industry,
        country=country
    )
    return business


@transaction.atomic
def update_business_data(
    business_uid: UUID,
    **kwargs
):
    business = Business.objects.filter(uid=business_uid).first()
    if not business:
        raise HttpError(404, "Business not found")
    industry_uid = kwargs.pop("industry", None)
    country_uid = kwargs.pop("country", None)
    industry = None
    country = None
    if industry_uid:
        industry = BusinessIndustry.objects.filter(uid=industry_uid).first()
    if country_uid:
        country = Country.objects.filter(uid=country_uid).first()

    business = business.update(
        **kwargs,
        industry=industry,
        country=country
    )

    return business


@transaction.atomic
def business_action(business_uid: UUID, action: Literal["archive", "pause", "move"]):
    business = Business.objects.get(uid=business_uid)

    if action == "archive":
        business.delete()
    elif action == "pause":
        pass
    elif action == "move":
        pass

    return business


def get_business_jobs_data(business_uid: UUID):
    business = Business.objects.get(uid=business_uid)

    shares_subquery = Subquery(
        JobPostMetrics.objects.filter(
            job_post__id=OuterRef("id")
        ).values("job_post__id").annotate(
            total=Sum("daily_email_shares")
        ).values("total")[:1],
        output_field=IntegerField()
    )

    views_subquery = Subquery(
        JobPostMetrics.objects.filter(
            job_post__id=OuterRef("id")
        ).values("job_post__id").annotate(
            total=Sum("weekly_views")
        ).values("total")[:1],
        output_field=IntegerField()
    )

    assignments_subquery = Subquery(
        BusinessUser.objects.filter(  # replace with your actual related model
            assigned_job_posts__id=OuterRef("id")
        ).values("id").annotate(
            total=Count("id")
        ).values("total")[:1],
        output_field=IntegerField()
    )

    job_posts = JobPost.objects.filter(
        job__created_by__business=business
    ).select_related("job__role").annotate(
        name=Case(
            When(job__role__isnull=False, then=F("job__role__name")),
            default=None,
            output_field=CharField(null=True)
        ),
        application_count=Count("jobapplication"),
        withdrawal_count=Count("jobapplicationwithdrawal"),
        shares=Coalesce(shares_subquery, 0),
        views=Coalesce(views_subquery, 0),
        assignments=Coalesce(assignments_subquery, 0)
    )

    jobs_created = job_posts.count()
    open_jobs = job_posts.filter(status=JobStatusType.POSTED.value).count()

    application_count = JobApplication.objects.filter(
        job_post__in=job_posts
    ).count()

    metrics = JobPostMetrics.objects.filter(
        job_post__in=job_posts
    )

    total_shares = metrics.aggregate(
        Sum("daily_email_shares")
    )["daily_email_shares__sum"] or 0

    total_views = metrics.aggregate(
        Sum("weekly_views")
    )["weekly_views__sum"] or 0

    withdrawal_reasons = []
    for reason in WithdrawalFeedbackType:
        feedback_type = JobApplicationWithdrawal.feedback_type_to_number(reason)
        count = JobApplicationWithdrawal.objects.filter(
            job_post__in=job_posts,
            feedback_type=feedback_type
        ).count()
        withdrawal_reasons.append({
            "reason": reason.value,
            "count": count
        })

    return job_posts.values("uid","name", "status", "withdrawal_count", "shares", "views", "assignments", "application_count"), {
        "jobs_created": jobs_created,
        "open_jobs": open_jobs,
        "applications": application_count,
        "shares": total_shares,
        "views": total_views,
        "withdrawal_reasons": withdrawal_reasons,
    }


def get_business_users_data(business_uid: UUID):
    business = Business.objects.get(uid=business_uid)
    return BusinessUser.objects.filter(business=business).select_related("user", "business", "added_by")


@transaction.atomic
def add_business_user_data(
    business_uid: UUID,
    **kwargs
):
    # Validate business exists
    business = Business.objects.filter(uid=business_uid).first()
    if not business:
        raise HttpError(404, "Business not found")

    # Validate required fields
    email = kwargs.get("email")
    first_name = kwargs.get("first_name")
    last_name = kwargs.get("last_name")
    role = kwargs.get("role")
    if role:
        role = role.value
    
    if not email:
        raise HttpError(400, "Email is required")
    if not first_name:
        raise HttpError(400, "First name is required")
    if not last_name:
        raise HttpError(400, "Last name is required")
    if not role:
        raise HttpError(400, "Role is required")
    
    # Check email uniqueness
    existing_user = User.objects.filter(email__iexact=email).first()
    if existing_user:
        if existing_user.deleted_at is not None:
            raise HttpError(400, "This email is not available")
        if BusinessUser.objects.filter(user=existing_user).exists():
            raise HttpError(400, "This email is not available")

    # Generate and capture password for admin-created user
    raw_password = User.objects.make_random_password()
    user = User.objects.create_user(
        email=email,
        password=raw_password,
        first_name=first_name,
        last_name=last_name,
        type=UserType.BUSINESS.value
    )
    
    # Admin creates users as active and verified (bypassing OTP/invite process)
    user.is_active = True
    user.email_verified = True
    user.save()

    business_user = BusinessUser.objects.create(
        business=business,
        user=user,
        role=role,
        status=BusinessUserStatusType.ACTIVE.value  # Active instead of PENDING
    )
    
    # Send account created email with login credentials
    
    async_task(
        send_admin_created_account_email,
        email=user.email,
        name=user.first_name,
        password=raw_password,
        account_type="business",
        business_name=business.name
    )

    return business_user

def ban_account(user: User):
    # TODO send an email to the banned account
    if BannedAccount.objects.filter(email__iexact=user.email, account_type=user.type).exists():
        return
    BannedAccount.objects.create(email=user.email, account_type=user.type)
    if hasattr(user, "talent"):
        user.talent.delete_account(banned=True)
        user.delete_account()
    elif hasattr(user, "businessuser"):
        user.businessuser.delete_account()
        user.delete_account()
    elif hasattr(user, "adminuser"):
        user.adminuser.hard_delete()
        user.delete_account()
    return


def toggle_account_status(user: User, is_active=True):
    if user.is_active == is_active:
        return user
    user.is_active = is_active
    user.save()
    if hasattr(user, "businessuser"):
        user.businessuser.status = BusinessUserStatusType.ACTIVE.value if is_active else BusinessUserStatusType.INACTIVE.value
        user.businessuser.save()

    # TODO: send an email regards account status
    return user


@transaction.atomic
def update_business_user_data(
    business_user_uid: UUID,
    **kwargs
):
    business_user = BusinessUser.objects.get(uid=business_user_uid)
    user = business_user.user

    role = kwargs.pop("role", None)
    email = kwargs.pop("email", None)
    password = kwargs.pop("password", None)

    if email is not None:
        existing_user = User.objects.filter(email__iexact=email).exclude(uid=user.uid).first()
        if existing_user:
            # Fix 2: block any existing non-deleted user, regardless of profile type
            if existing_user.deleted_at is None:
                raise ValidationError("This email is not available")
        user.email = email
        user.email_verified = False

    user = user.update(**kwargs)

    if password:
        user.set_password(password)

    user.save()

    if role:
        business_user.role = role

    business_user.save()

    return business_user


@transaction.atomic
def delete_business_user_data(business_user_uid: UUID):
    business_user = BusinessUser.objects.filter(uid=business_user_uid).first()
    if not business_user:
        raise HttpError(404, "Business user not found")

    if business_user.role == BusinessUserRoleType.OWNER.value:
        raise HttpError(400, "Not allowed! you cannot delete owner account")

    has_jobs = Job.objects.annotate(
        is_posted_by_business_user=Exists(
            JobPost.objects.filter(
                job__pk=OuterRef("pk"), posted_by=business_user
            )
        ),
        is_recruiter=Exists(
            JobPost.objects.filter(
                job__pk=OuterRef("pk"), recruiter=business_user
            )
        ),
    ).filter(
        is_recruiter=True
    ).exists()
    if has_jobs and business_user.status != BusinessUserStatusType.PENDING.value:
        raise HttpError(403,
                        "Not Allowed! Please reassign all jobs allocated to this user before proceeding with deletion")
    created_jobs = Job.objects.filter(created_by=business_user)
    business_user = BusinessUser.objects.filter(business=business_user.business).exclude(id=business_user.id).order_by("?").first()
    if not business_user and (created_jobs.exists()):
        raise HttpError(403, "This user has created some jobs and cannot be deleted")
    BusinessUser.objects.filter(uid=business_user_uid).hard_delete()
    User.objects.filter(id=business_user.user.id).hard_delete()
    return {"message": "Business user deleted successfully"}

def get_talent_users_data():
    return Talent.objects.all().select_related("user", "role", "country")


def get_talent_user_data(talent_uid: UUID):
    talent = Talent.objects.filter(uid=talent_uid).select_related("user", "role", "country").first()
    if not talent:
        raise HttpError(404, "Talent not found")
    return talent


def get_talent_applications_data(talent_uid: UUID):
    talent = Talent.objects.filter(uid=talent_uid).first()
    if not talent:
        raise HttpError(404, "Talent not found")
    
    job_applications = JobApplication.objects.filter(applicant=talent)
    queryset = job_applications.select_related("job_post", "job_post__job", "job_post__job__role", "job_post__job__created_by__business").\
        annotate(
        job=Case(
            When(job_post__job__role__isnull=False, then=F("job_post__job__role__name")),
            default=Value(None)
        ),
        company=Case(
            When(job_post__job__created_by__business__isnull=False, then=F("job_post__job__created_by__business__name")),
            default=Value(None)
        ),
        job_status=F("job_post__status"),
        date_applied=F("created_at__date"),
        withdrawals=Exists(
            JobApplicationWithdrawal.objects.filter(
                job_post=OuterRef("job_post")
            )
        ),
        application_status=F("stage__phase")
    ).values(
        "uid", "job", "company", "job_status", "date_applied", "withdrawals", "application_status"
    )
    
    applications_count = job_applications.count()
    rejected_count = job_applications.filter(stage__phase=PhaseType.REJECTED.value).count()
    withdrawals_count = JobApplicationWithdrawal.objects.filter(
        job_post__in=job_applications.values("job_post")
    ).count()
    
    job_posts = job_applications.values_list("job_post", flat=True)
    shares = JobPostMetrics.objects.filter(
        job_post__in=job_posts
    ).aggregate(total_shares=Sum('daily_email_shares'))['total_shares'] or 0
    views = JobPostMetrics.objects.filter(
        job_post__in=job_posts
    ).aggregate(total_views=Sum('weekly_views'))['total_views'] or 0
    
    return queryset, {
        "applications": applications_count,
        "rejected": rejected_count,
        "withdrawals": withdrawals_count,
        "job_shares": shares,
        "job_views": views
    }


@transaction.atomic
def create_talent_user_data(**kwargs):
    return talent_services.create_talent_profile_service(kwargs)


@transaction.atomic
def update_talent_user_data(talent_uid: UUID, **kwargs):
    talent = Talent.objects.filter(uid=talent_uid).select_related("user").first()
    if not talent:
        raise HttpError(404, "Talent not found")
    
    return talent_services.update_talent_profile_service(talent, kwargs)


def normalize_month(value):
    """Convert anything to date(year, month, 1)"""
    if isinstance(value, datetime):
        return date(value.year, value.month, 1)
    if isinstance(value, date):
        return value.replace(day=1)
    raise ValueError(f"Unsupported month type: {type(value)}")


def fill_monthly_gaps(data, page=None, page_size=None):
    # Normalize list
    if isinstance(data, list):
        data_list = data
    elif isinstance(data, Iterable) and not isinstance(data, (str, dict)):
        data_list = list(data)
    else:
        data_list = []

    if not data_list:
        return {
            "results": [],
            "count": 0,
            "number_of_pages": 0,
            "next_page": None,
            "previous_page": None,
        } if page else []

    # Normalize ALL months
    for row in data_list:
        row["month"] = normalize_month(row["month"])

    # Sort newest first
    data_list.sort(key=lambda x: x["month"], reverse=True)

    sample = data_list[0]
    zero_fields = {k: 0 for k in sample if k != "month"}

    by_month = {row["month"]: row for row in data_list}

    # 🔥 KEY FIX: start from CURRENT month
    today = date.today()
    end = date(today.year, today.month, 1)

    # oldest data point
    start = data_list[-1]["month"]

    total = (end.year - start.year) * 12 + (end.month - start.month) + 1

    def generate_months(year, month, count):
        for _ in range(count):
            yield year, month
            month -= 1
            if month < 1:
                month = 12
                year -= 1

    # No pagination
    if page is None or page_size is None:
        result = []
        for y, m in generate_months(end.year, end.month, total):
            key = date(y, m, 1)
            result.append(by_month.get(key, {"month": key, **zero_fields}))
        return result

    # Pagination
    number_of_pages = ceil(total / page_size)
    p = max(1, min(page, number_of_pages))
    skip = (p - 1) * page_size

    end_index = end.year * 12 + end.month - 1
    current_index = end_index - skip

    cur_year = current_index // 12
    cur_month = current_index % 12 + 1

    result = []

    for y, m in generate_months(cur_year, cur_month, page_size):
        if (y, m) < (start.year, start.month):
            break
        key = date(y, m, 1)
        result.append(by_month.get(key, {"month": key, **zero_fields}))

    return {
        "count": total,
        "number_of_pages": number_of_pages,
        "next_page": p + 1 if p < number_of_pages else None,
        "previous_page": p - 1 if p > 1 else None,
        "results": result,
    }

def get_page_metric_data(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
):
    queryset = PageMetric.objects
    if start_date:
        queryset = queryset.filter(month__gte=start_date.date())
    if end_date:
        queryset = queryset.filter(month__lte=end_date.date())

    return fill_monthly_gaps(queryset.annotate(
        load_time=Case(
            When(count=0, then=Value(0.0)),
            default=F('total_time')/F('count'),
            output_field=FloatField()
        )
    ).values("month")
     .annotate(average_load_time=Avg('load_time'))
     .order_by("-month").values("month", "average_load_time"),
                             page, page_size)

def get_api_metric_data(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
):
    queryset = APIMetric.objects
    if start_date:
        queryset = queryset.filter(month__gte=start_date.date())
    if end_date:
        queryset = queryset.filter(month__lte=end_date.date())
    return fill_monthly_gaps(queryset.annotate(
        load_time=Case(
            When(count=0, then=Value(0.0)),
            default=F('total_time')/F('count'),
            output_field=FloatField()
        )
    ).values("month")
    .annotate(average_load_time=Avg('load_time'))
    .order_by("-month").values("month", "average_load_time"),
                             page, page_size)

def get_talent_signups_data(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
):
    queryset = Talent.objects.annotate(
        signup_date=Func(F('created_at'), function='EXTRACT', template='"%m-%Y"')
    ).annotate(
        month=TruncMonth("created_at")
    )
    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)

    return fill_monthly_gaps(queryset.annotate(month=TruncMonth("created_at"))
                             .values("month")
                             .annotate(signups=Count('id'))
                             .order_by("-month")
                             .values("month", "signups"),page, page_size)


def get_talent_profile_completion_data(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
):
    queryset = add_profile_completion_annotation(
        Talent.objects.all()
    )
    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)

    return fill_monthly_gaps(
        queryset
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            complete=Count('id', filter=Q(complete_profile=True)),
            semi_complete=Count('id', filter=Q(semi_complete_profile=True)),
            incomplete=Count('id', filter=Q(complete_profile=False, semi_complete_profile=False)),
        )
        .order_by("-month").values("month", "complete", "semi_complete", "incomplete"),
        page, page_size
    )

def pause_business(business):
    business.paused = True
    business.save()
    # TODO: send email to business regarding pause
    return business

def resume_business(business):
    business.paused = False
    business.save()
    # TODO: send email to business regarding resume
    return business


def delete_business(business):
    from chats.models import Conversation
    JobAlert.objects.filter(jobs__created_by__business=business).all().hard_delete()
    Job.objects.filter(created_by__business=business).all().hard_delete()
    Conversation.objects.filter(users__businessuser__business=business).all().hard_delete()
    User.objects.filter(businessuser__business=business).all().hard_delete()
    JobPostTag.objects.filter(business=business).all().hard_delete()
    BusinessClient.objects.filter(business=business).all().hard_delete()
    Business.objects.filter(id=business.id).hard_delete()
    return


def pause_resume_business(business, action):
    if action == "pause":
        return pause_business(business)
    elif action == "resume":
        return resume_business(business)
    else:
        raise HttpError(400, "Invalid action. Must be 'pause' or 'resume'")

