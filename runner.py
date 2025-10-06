import os

import django
from django.db.models import Count, Q, F, Case, Value, When


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Talent, User
from jobs.models import JobApplication
from jobs.enums import PhaseType
from accounts.enums import GenderType

User.objects.filter(gender='non-binary').update(gender=GenderType.OTHERS.value)

talents = Talent.objects.annotate(
    application_count=Count("jobapplication",
          filter=Q(jobapplication__stage__created_by__business__uid="3bd32bf1-44c4-46cc-93eb-d8384c4da121",
                   ),
      distinct=True),
gender=Case(
    When(user__gender__isnull=False, then=F("user__gender")),
    default=Value('others'),
)).filter(
    application_count__gt=0
)
aggregate = talents.values("gender").annotate(
    count=F("gender")
)

for gender in GenderType.values():
    print(gender, talents.filter(gender=gender).count())


for talent in aggregate:
    print(talent)















