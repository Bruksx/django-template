from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from django.utils import timezone
from django_q.models import Schedule
from pydantic import EmailStr

from accounts.models import Business, BusinessUser
from accounts.services.common import average_days_to_hire, average_days_per_stage, applicant_to_hire_ratio, \
    applicant_dropout_ratio, applicant_per_phase, applicant_per_stage, hired_applicants_per_phase_timeline, \
    total_applicants, average_applicants_per_job, average_applicants_per_client, average_applicants_per_recruiter, \
    best_jobs_by_applications, worst_jobs_by_applications, best_clients_by_applications, worst_clients_by_applications, \
    applications_per_location, applications_per_experience, applications_per_demographics, withdrawal_reason_count


def create_business_workflows(business_id):
    from settings.models import WorkFlowStage
    from jobs.enums import PhaseType
    business_user = BusinessUser.objects.filter(business_id=business_id).first()
    if not business_user:
        return
    phases = (PhaseType.NEW.value, PhaseType.HIRED.value, PhaseType.REJECTED.value)

    for phase in phases:
        workflow = WorkFlowStage.objects.filter(created_by=business_user, phase=phase).first()
        if not workflow:
            WorkFlowStage.objects.create(created_by=business_user, phase=phase, name=str(phase).title(), phase_order=PhaseType.values().index(phase))
    return




def pipeline_dashboard_data(business: Optional[Business]=None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, role: Optional[UUID] = None, client: Optional[str]=None):
    data = dict()
    data["avg_days_to_hire"] = average_days_to_hire(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["avg_days_to_hire_per_stage"] = average_days_per_stage(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["applicant_hire_ratio"] = applicant_to_hire_ratio(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["dropout_ratio"] = applicant_dropout_ratio(business=business, start_date=start_date, end_date=end_date, role=role, client=client)

    data["applicant_per_phase"] = applicant_per_phase(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["applicant_per_stage"] = applicant_per_stage(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["phase_timeline"] = hired_applicants_per_phase_timeline(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return data


def recruitment_dashboard_data(business: Optional[Business]=None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, role: Optional[UUID] = None, client: Optional[str]=None):
    data = dict()
    data["total_applicants"] = total_applicants(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["avg_applicants_per_job"] = average_applicants_per_job(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["avg_applicants_per_client"] = average_applicants_per_client(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["avg_applicants_per_recruiter"] = average_applicants_per_recruiter(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return data


def applicant_dashboard_data(business: Optional[Business]=None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, role: Optional[UUID] = None, client: Optional[str]=None):
    data = dict()
    data["best_applicant_by_job"] = best_jobs_by_applications(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["worst_applicant_by_job"] = worst_jobs_by_applications(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["best_applicant_by_client"] = best_clients_by_applications(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["worst_applicant_by_client"] = worst_clients_by_applications(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["application_by_location"] = applications_per_location(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["application_by_gender"] = applications_per_demographics(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["application_by_experience"] = applications_per_experience(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    data["withdrawal_reasons"] = withdrawal_reason_count(business=business, start_date=start_date, end_date=end_date, role=role, client=client)
    return data



def handle_invited_talents(emails: List[EmailStr], user):
    Schedule.objects.create(
        name="Send Talent Invitation Email 1",
        func="accounts.tasks.send_talent_invitation_email",
        schedule_type=Schedule.ONCE,
        args=[emails, 1, "en"],
        next_run=timezone.now() + timedelta(minutes=10)
    )

    Schedule.objects.create(
        name="Send Talent Invitation Email 2",
        func="accounts.tasks.send_talent_invitation_email",
        schedule_type=Schedule.ONCE,
        args=[emails, 2, "en"],
        next_run=timezone.now() + timedelta(days=2)
    )

    Schedule.objects.create(
        name="Send Talent Invitation Email 3",
        func="accounts.tasks.send_talent_invitation_email",
        schedule_type=Schedule.ONCE,
        args=[emails, 3, "en"],
        next_run=timezone.now() + timedelta(days=7)
    )

    user.invitation_no_sent += 1
    user.invitation_sent_at = timezone.now()
    user.save()
    return









