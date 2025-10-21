import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Experience
from jobs.models import JobPost
from core.enums import SalaryType

Experience.objects.update(salary_type=SalaryType.ANNUALLY.value, salary_bonus_type=SalaryType.ANNUALLY.value)
JobPost.objects.update(salary_type=SalaryType.ANNUALLY.value, salary_bonus_type=SalaryType.ANNUALLY.value)
