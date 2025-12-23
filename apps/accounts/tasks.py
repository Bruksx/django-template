from accounts.models import Talent, User
from accounts.queries import add_profile_completion_annotation

from helpers.email.accounts import send_incomplete_profile_reminder_email


def remind_incomplete_profiles_task(batch_size=200):
    talent_ids = add_profile_completion_annotation(
        Talent.objects.all()
    ).filter(complete_profile=False).only("id").values_list("id", flat=True)

    talent_count = talent_ids.count()
    batches, remainder = divmod(talent_count, batch_size)
    for batch in range(batches):
        emails = list(User.objects.filter(talent__id__in=talent_ids[(batch * batch_size):((batch + 1) * batch_size)]).only("email").values_list("email", flat=True))
        send_incomplete_profile_reminder_email(emails=emails)
    if remainder > 0:
        emails = list(User.objects.filter(talent__id__in=talent_ids[-remainder:]).only(
            "email").values_list("email", flat=True))
        send_incomplete_profile_reminder_email(emails=emails)