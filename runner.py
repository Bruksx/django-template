import os

import django
from django.db.models import Count

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Talent

talents = Talent.objects.annotate(skill_count=Count('skills')).filter(skill_count__gt=0)
for talent in talents:
    print(talent.skills.values("uid"))






