from accounts.models import Talent, User
from accounts.queries import add_profile_completion_annotation

from helpers.email.accounts import send_incomplete_profile_reminder_email


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
