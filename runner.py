import os

import django

from apps.accounts.constants import DEPARTMENT_AND_SKILLS_OLD

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
