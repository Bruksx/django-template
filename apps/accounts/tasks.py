from datetime import timedelta
from typing import List

from django.utils import timezone

from accounts.models import Talent, User
from accounts.queries import add_profile_completion_annotation
from config import settings
from enums import SourceType
from helpers.email.accounts import send_first_talent_invitation_email, send_second_talent_invitation_email, \
    send_third_talent_invitation_email
from helpers.email.accounts import send_talent_account_activation_email
from helpers.email.utils import send_email


def remind_incomplete_profiles_task(batch_size=200):
    talent_ids = (
        add_profile_completion_annotation(Talent.objects.all())
        .filter(complete_profile=False)
        .order_by("id")
        .values_list("id", flat=True)
    )

    total = talent_ids.count()

    for start in range(0, total, batch_size):
        batch_ids = talent_ids[start : start + batch_size]

        emails = list(
            User.objects.filter(talent__id__in=batch_ids)
            .values_list("email", flat=True)
        )

        # send_incomplete_profile_reminder_email(emails=emails)



def send_weekly_report_of_candidates():
    if settings.DEBUG is True:
        return
    last_week = timezone.now() - timedelta(days=7)
    queryset = add_profile_completion_annotation(
        Talent.objects.all()
    )
    total = queryset.count()
    total_last_week = queryset.exclude(created_at__gt=last_week).count()

    total_completed = queryset.filter(complete_profile=True).count()
    total_semi_completed = queryset.filter(semi_complete_profile=True).count()
    total_incompleted = queryset.filter(semi_complete_profile=False).count()

    completed = queryset.filter(complete_profile=True, created_at__gt=last_week).count()
    semi_completed = queryset.filter(semi_complete_profile=True, created_at__gt=last_week).count()
    incompleted = queryset.filter(semi_complete_profile=False, created_at__gt=last_week).count()

    send_email(
        subject="Talent Completion Profile Weekly Report",
        emails=["bryan@1840andco.com", "ohaegbulouis@gmail.com", "khurshidu@1840andco.com", "emilyph@1840andco.com"],
        plain_body=f"""
Total Number of Talents Today: {total} \n
Total Number of Talents Last Week: {total_last_week} \n\n

This Week's Data \n\n
Number of talents with complete profiles:   {completed + semi_completed}\n
Number of talents with incomplete profiles:    {incompleted}\n
        """
    )

    send_email(
        subject="Talent Completion Profile Weekly Report",
        emails=["ohaegbulouis@gmail.com", "khurshidu@1840andco.com"],
        plain_body=f"""
    Total Number of Talents Today: {total} \n
    Total Number of Talents Last Week: {total_last_week} \n\n
    Total Number of Talents Completed: {total_completed + total_semi_completed} \n
    Total Number of Talents Incompleted: {total_incompleted} \n\n
    

    This Week's Data \n\n
    Number of talents with complete profiles:   {completed + semi_completed}\n
    Number of talents with incomplete profiles:    {incompleted}\n
            """
    )

def send_talent_invitation_email(emails: List[str], email_order: int=1, lang="en"):
    already_sent = set(Talent.objects.filter(user__email__in=emails).values_list("user__email", flat=True))
    emails = list(set(emails) - already_sent)
    if not emails:
        return
    if email_order == 1:
        send_first_talent_invitation_email(emails, lang=lang)
    elif email_order == 2:
        send_second_talent_invitation_email(emails, lang=lang)
    elif email_order == 3:
        send_third_talent_invitation_email(emails, lang=lang)
    return


def deactivate_inactive_talents():
    last_30_days = timezone.now() - timedelta(days=30)
    talents = Talent.objects.select_related("user").exclude(is_active=False)
    talents = talents.filter(user__last_login__lte=last_30_days)
    talents.update(is_active=False, visible=False)
    for talent in talents.iterator():
        send_talent_account_activation_email(email=talent.user.email, fullname=talent.user.full_name, status="inactive")
    return

def deactivate_incomplete_talent_accounts():
    last_30_days = timezone.now() - timedelta(days=30)
    talents = add_profile_completion_annotation(Talent.objects.all())
    talents = talents.filter(created_at__lte=last_30_days, semi_complete_profile=False)
    talents.update(is_active=False, visible=False)
    for talent in talents.iterator():
        send_talent_account_activation_email(email=talent.user.email, fullname=talent.user.full_name, status="incomplete")
    return

def send_weekly_report_of_talent_sources():
    if settings.DEBUG is True:
        return
    last_week = timezone.now() - timedelta(days=7)
    indeed_queryset = Talent.objects.filter(source=SourceType.INDEED.value)
    linkedin_queryset = Talent.objects.filter(source=SourceType.LINKEDIN.value)
    linked_total = linkedin_queryset.count()
    indeed_total = indeed_queryset.count()
    total_linked_last_week = linkedin_queryset.exclude(created_at__gt=last_week).count()
    total_indeed_last_week = indeed_queryset.exclude(created_at__gt=last_week).count()

    send_email(
        subject="Talent Profile Source Weekly Report",
        emails=["ohaegbulouis@gmail.com", "khurshidu@1840andco.com"],
        plain_body=f"""
    Total Number of Talents from LinkedIn Last Week: {total_linked_last_week} \n
    Total Number of Talents from Indeed Last Week: {total_indeed_last_week} \n\n

    Number of talents from LinkedIn:   {linked_total}\n
    Number of talents from Indeed:    {indeed_total}\n
            """
    )