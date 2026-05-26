from datetime import datetime, timedelta, date
from typing import Optional
from uuid import UUID

from django.db.models import Func, F, Q
from django.db.models import Sum, Avg, Count, OuterRef, Exists, Subquery
from django.db.models.functions import TruncDate, Round
from django.utils import timezone

from accounts.models import Business
from jobs.enums import PhaseType, WithdrawalFeedbackType
from jobs.models import TalentApplicationStageTimeline, JobApplication, JobApplicationWithdrawal


class InitCap(Func):
    function = "INITCAP"

def get_talent_application_stage_timeline(queryset, business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: Optional[UUID]=None, client: Optional[UUID]=None):
    queryset = TalentApplicationStageTimeline.add_time_spent_annotation(queryset)
    if business:
        queryset = queryset.filter(stage__created_by__business=business)
    # filtering based on date hired not date created
    if start_date and not end_date:
        queryset = queryset.filter(created_at__gte=start_date)
    elif end_date and not start_date:
        queryset = queryset.filter(created_at__lte=end_date)
    elif start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])
    if role:
        queryset = queryset.filter(job_role__uid=role)
    if client:
        queryset = queryset.filter(application__job_post__job__hiring_company_name=client)
    return queryset

def get_application_queryset(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = JobApplication.objects.select_related("stage__created_by__business", "job_post__job", "stage", "applicant__user", "recruiter__user" )
    if business:
        queryset = queryset.filter(stage__created_by__business=business)
    if start_date and not end_date:
        queryset = queryset.filter(created_at__gte=start_date)
    elif end_date and not start_date:
        queryset = queryset.filter(created_at__lte=end_date)
    elif start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])
    if role:
        queryset = queryset.filter(job_post__job__role__uid=role)
    if client:
        queryset = queryset.filter(job_post__job__hiring_company_name=client)
    return queryset


def average_days_to_hire(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: Optional[UUID]=None, client: Optional[UUID]=None):
    queryset = get_talent_application_stage_timeline(
        queryset=TalentApplicationStageTimeline.objects.filter(
            application__stage__phase=PhaseType.HIRED.value).exclude(
            stage__phase=PhaseType.HIRED.value
        ),
        business=business, start_date=start_date, end_date=end_date, role=role, client=client)

    return (queryset.values("application").annotate(total_time=Sum("time_spent")).aggregate(
        days_to_hire=Round(Avg("total_time"), 0)
    )["days_to_hire"] or 0)

def average_days_per_stage(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_talent_application_stage_timeline(
        queryset=TalentApplicationStageTimeline.objects,
        business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return (queryset.values("stage").annotate(avg_time_spent=Avg("time_spent")).aggregate(
        avg_stage_time_spent=Round(Avg("avg_time_spent"), 0)
    )['avg_stage_time_spent'] or 0)


def applicant_to_hire_ratio(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    total_hired = queryset.filter(stage__phase=PhaseType.HIRED.value).count()
    total_application = queryset.count()
    return int(total_hired/total_application * 100) if total_application > 0 else 0


def applicant_dropout_ratio(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    total_rejected = queryset.filter(stage__phase=PhaseType.REJECTED.value).count()
    total_application = queryset.count()
    return int(total_rejected / total_application * 100) if total_application > 0 else 0



def applicant_per_phase(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    application = queryset.distinct("applicant").count()
    res = [dict(phase="Applicants", count=application)]
    queryset = (queryset.order_by("stage__phase_order")
                .annotate(phase=InitCap("stage__phase")).values("phase")
                .annotate(count=Count("applicant", distinct=True)).values("phase", "count"))
    res.extend(queryset)
    return res

def applicant_per_stage(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    application = queryset.distinct("applicant").count()
    res = [dict(stage_name="Applicants", count=application)]

    queryset = (queryset.order_by("stage__phase_order", "stage__order")
                .annotate(stage_name=InitCap("stage__name")).values("stage_name")
                .annotate(count=Count("applicant", distinct=True)).values("stage_name", "count"))
    res.extend(queryset)
    return res


def hired_applicants_per_stage_timeline(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_talent_application_stage_timeline(
        queryset=TalentApplicationStageTimeline.objects.filter(
            application__stage__phase=PhaseType.HIRED.value).exclude(
            stage__phase=PhaseType.HIRED.value
        ),
        business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    queryset = queryset.order_by("stage__phase_order", "stage__order").annotate(stage_name=InitCap("stage__name"))
    graph = queryset.values("stage_name").annotate(avg_days_spent=Avg("time_spent")).values("stage_name", "avg_days_spent")
    days_to_hire = graph.aggregate(days_to_hire=Sum("avg_days_spent"))["days_to_hire"] or 0
    return {
        "days_to_hire": days_to_hire,
        "graph": graph
    }


def hired_applicants_per_phase_timeline(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = TalentApplicationStageTimeline.add_time_spent_annotation(
        TalentApplicationStageTimeline.objects.filter(
            application__stage__phase=PhaseType.HIRED.value).exclude(
            stage__phase=PhaseType.HIRED.value
        ))
    if business:
        queryset = queryset.filter(stage__created_by__business=business)
    # filtering based on date hired not date created
    if start_date and not end_date:
        queryset = queryset.filter(created_at__gte=start_date)
    elif end_date and not start_date:
        queryset = queryset.filter(created_at__lte=end_date)
    elif start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])
    if role:
        queryset = queryset.filter(job_role__uid=role)
    if client:
        queryset = queryset.filter(application__job_post__job__hiring_company_name=client)
    queryset = queryset.order_by("stage__phase_order").annotate(phase=InitCap("stage__phase"))
    graph = queryset.values("phase").annotate(avg_days_spent=Round(Avg("time_spent"), 0)).values("phase", "avg_days_spent")
    days_to_hire = round(graph.aggregate(days_to_hire=Sum("avg_days_spent"))["days_to_hire"] or 0)
    return {
        "days_to_hire": days_to_hire,
        "graph": graph
    }


def total_applicants(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return queryset.distinct("applicant").count()


def average_applicants_per_job(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return round(queryset.values("job_post__job").annotate(count=Count("applicant", distinct=True)).values("job_post__job", "count").aggregate(average=Avg("count"))["average"] or 0)

def average_applicants_per_client(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return round(queryset.values("job_post__job__hiring_company_name").annotate(count=Count("applicant", distinct=True)).values("job_post__job__hiring_company_name", "count").aggregate(average=Avg("count"))["average"] or 0)

def average_applicants_per_recruiter(business: Optional[Business]=None, start_date: Optional[datetime]=None, end_date: Optional[datetime]=None, role: UUID=None, client: str=None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return round(queryset.values("recruiter").annotate(count=Count("applicant", distinct=True)).values("recruiter", "count").aggregate(average=Avg("count"))["average"] or 0)


def application_hires_graph_data(business: Optional[Business] = None,
                                     start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                                     role: Optional[UUID] = None, client: Optional[str] = None,
                                     first_date: Optional[date] = None,
                                     last_date: Optional[date] = None,
                                     ):
    if not first_date or not last_date:
        first_date = timezone.now().date() - timedelta(days=30)
        last_date = timezone.now().date()
    if last_date < first_date:
        return []

    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    applications = queryset.annotate(day=TruncDate("created_at")).values("day").annotate(applications=Count("id")).values("day", "applications")
    hires = queryset.filter(stage_date_updated__isnull=False, stage__phase=PhaseType.HIRED.value).annotate(day=TruncDate("stage_date_updated")).values("day").annotate(hires=Count("id")).values("day", "hires")
    applications = applications.filter(day__range=[first_date, last_date]).order_by("-day")
    hires = hires.filter(day__range=[first_date, last_date]).order_by("-day")
    applications = {a["day"]: a["applications"] for a in applications}
    hires = {h["day"]: h["hires"] for h in hires}
    res = []
    count = (last_date - first_date).days
    for day in range(0, count + 1):
        day = first_date + timedelta(days=day)
        res.append({
            "day": day,
            "applications": applications.get(day, 0),
            "hires": hires.get(day, 0)
        })
    return res


def recruiter_hires_graph_data(business: Optional[Business] = None,
                                     start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                                     role: Optional[UUID] = None, client: Optional[str] = None):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    queryset = queryset.filter(stage__phase=PhaseType.HIRED.value)
    graph = queryset.values("recruiter").annotate(count=Count("id"), recruiter_name=F("recruiter__user__fullname")).values("recruiter_name", "count")
    return graph, queryset.count()

def stuck_applications(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(
        business=business,
        start_date=start_date,
        end_date=end_date,
        role=role,
        client=client
    )

    queryset = queryset.exclude(
        stage__phase__in=[PhaseType.HIRED.value, PhaseType.REJECTED.value]
    )

    from jobs.models import TalentApplicationStageTimeline
    timeline_qs = TalentApplicationStageTimeline.add_time_spent_annotation(
        TalentApplicationStageTimeline.objects.filter(
            application_id=OuterRef("id"),
            stage_id=OuterRef("stage_id")
        )
    )

    # Exists check (fast)
    stuck_subquery = timeline_qs.filter(time_spent__gt=5)

    # Proper scalar subquery (returns ONE column)
    days_in_stage_subquery = timeline_qs.values("time_spent")[:1]

    queryset = queryset.annotate(
        talent=F("applicant__user__fullname"),
        job=F("job_post__job__role__name"),
        client=F("job_post__job__hiring_company_name"),
        phase=InitCap("stage__phase"),
        stage_name=InitCap("stage__name"),
        stuck=Exists(stuck_subquery),
        days_in_stage=Subquery(days_in_stage_subquery)
    ).filter(stuck=True).values("uid", "talent", "job", "client", "phase", "stage_name", "days_in_stage").order_by("-days_in_stage").distinct()

    return queryset


def recent_hires(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    queryset = queryset.filter(stage__phase=PhaseType.HIRED.value)
    return queryset.annotate(
        role=F("job_post__job__role__name"),
        talent=F("applicant__user__fullname"),
        hired_by=F("recruiter__user__fullname")
    ).values("uid", "role", "talent", "hired_by").order_by("-created_at").distinct()



def best_jobs_by_applications(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return queryset.annotate(job=F("job_post__job__role__name")).values("job").annotate(count=Count("id")).values("job", "count").order_by("-count").distinct()[:10]

def worst_jobs_by_applications(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return queryset.annotate(job=F("job_post__job__role__name")).values("job").annotate(count=Count("id")).values("job", "count").order_by("count").distinct()[:10]


def best_clients_by_applications(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return queryset.annotate(client=F("job_post__job__hiring_company_name")).values("client").annotate(count=Count("id")).values("client", "count").order_by("-count").distinct()[:10]

def worst_clients_by_applications(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return queryset.annotate(client=F("job_post__job__hiring_company_name")).values("client").annotate(count=Count("id")).values("client", "count").order_by("count").distinct()[:10]


def applications_per_location(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return queryset.annotate(location=F("job_post__country__name")).values("location").annotate(count=Count("id")).values("location", "count").order_by("-count").distinct()

def applications_per_demographics(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return queryset.annotate(demographics=F("applicant__user__gender")).values("demographics").annotate(count=Count("id")).values("demographics", "count").order_by("-count").distinct()


def applications_per_experience(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    experience_set = ((0, 1), (1, 3), (3, 5), (5, 7), (7, 10), 10)
    get_label = lambda x: f"{x if isinstance(x, int) else f'{x[0]}-{x[1]}'} Years"
    get_query = lambda x:  Q(applicant__years_of_experience__gte=x[0]) & Q(applicant__years_of_experience__lte=x[1]) if isinstance(x, tuple) else Q(applicant__years_of_experience__gt=x)
    return [
        {
            "experience": get_label(x),
            "count": queryset.filter(get_query(x)).count()
        }
        for x in experience_set
    ]


def withdrawal_reason_count(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = JobApplicationWithdrawal.objects.prefetch_related("job_post")
    if business:
        queryset = queryset.filter(
        job_post__recruiter__business=business
    )

    if start_date and not end_date:
        queryset = queryset.filter(created_at__gte=start_date)
    elif end_date and not start_date:
        queryset = queryset.filter(created_at__lte=end_date)
    elif start_date and end_date:
        queryset = queryset.filter(created_at__range=[start_date, end_date])
    if role:
        queryset = queryset.filter(job_post__job__role_id=role)
    if client:
        queryset = queryset.filter(job_post__job__hiring_company_name=client)
    result_data_list = []
    for reason in WithdrawalFeedbackType:
        feed_back_type = JobApplicationWithdrawal.feedback_type_to_number(reason)
        result_data_list.append({
            "reason": reason.value,
            "count": queryset.filter(
                feedback_type=feed_back_type
            ).count()
        })
    return {
        "count": queryset.count(),
        "graph": sorted(result_data_list, key=lambda x: x["count"], reverse=True)
    }

def application_pipeline_ratio(
    business: Optional[Business] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    role: Optional[UUID] = None,
    client: Optional[str] = None
):
    queryset = get_application_queryset(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    queryset = (queryset.exclude(
        stage__phase=PhaseType.REJECTED.value
    ).order_by("stage__phase_order", "stage__order")
                .annotate(stage_name=InitCap("stage__name")).values("stage_name")
                .annotate(count=Count("applicant", distinct=True)).values("stage_name", "count"))
    result = []
    count = queryset.count()
    for i in range(count):
        if i + 1 == count:
            break
        result.append({
            "first_stage": queryset[i],
            "second_stage": queryset[i + 1],
            "ratio": round((queryset[i+1]["count"] / queryset[i]["count"]) * 100, 1)
        })
    return result

