import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from jobs.models import JobPost
from accounts.models import Talent
from core.models import Language

talents = Talent.objects.all()






