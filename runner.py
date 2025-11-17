import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Talent

for talent in Talent.objects.iterator():
	years, month = talent.calculate_years_of_experience()
	talent.update(years_of_experience=years, months_of_experience=month)