from datetime import timedelta

from accounts.models import Talent, User
from accounts.queries import add_profile_completion_annotation
from django.utils import timezone

from config import settings
from helpers.email.accounts import send_incomplete_profile_reminder_email
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
Number of talents with complete profiles:   {completed}\n
Number of talents with semi complete profiles:   {semi_completed}\n
Number of talents with incomplete profiles:    {incompleted}\n
        """
    )

    send_email(
        subject="Talent Completion Profile Weekly Report",
        emails=["ohaegbulouis@gmail.com", "khurshidu@1840andco.com"],
        plain_body=f"""
    Total Number of Talents Today: {total} \n
    Total Number of Talents Last Week: {total_last_week} \n\n
    Total Number of Talents Completed: {total_completed} \n
    Total Number of Talents Semi Completed: {total_semi_completed} \n
    Total Number of Talents Incompleted: {total_incompleted} \n\n
    

    This Week's Data \n\n
    Number of talents with complete profiles:   {completed}\n
    Number of talents with semi complete profiles:   {semi_completed}\n
    Number of talents with incomplete profiles:    {incompleted}\n
            """
    )
