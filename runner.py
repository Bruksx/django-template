import os
from uuid import UUID

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from jobs.models import JobPost
from core.models import City, State

from django.db.models import Q

for jp in JobPost.objects.filter(Q(city__isnull=False)|Q(province__isnull=False)).iterator():
    city, province = None, None
    if jp.city:
        try:
            uuid = UUID(jp.city)
            city = City.objects.get(uid=uuid)
        except:
            city = City.objects.filter(name__icontains=jp.city).first()
    if jp.province:
        try:
            uuid = UUID(jp.province)
            province = State.objects.get(uid=uuid)
        except:
            province = State.objects.filter(name__icontains=jp.province).first()

    if city:
        jp.suburb = city
    if province:
        jp.state = province
    jp.save()

print("update state and city for job posts")
