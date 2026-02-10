from accounts.models import Talent, User
from accounts.queries import add_profile_completion_annotation

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

        send_incomplete_profile_reminder_email(emails=emails)



def send_weekly_report_of_candidates():
    queryset = add_profile_completion_annotation(
        Talent.objects.all()
    )
    completed = queryset.filter(complete_profile=True).count()
    semi_completed = queryset.filter(semi_complete_profile=True).count()
    incompleted = queryset.filter(semi_complete_profile=False).count()

    send_email(
        subject="Talent Completion Profile Weekly Report",
        emails=["bryan@1840andco.com"],
        plain_body=f"""
Number of talents with complete profiles:   {completed}
Number of talents with semi complete profiles:   {semi_completed}
Number of talents with incomplete profiles:    {incompleted}
        """
    )
