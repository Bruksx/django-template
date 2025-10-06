import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import User
from accounts.enums import GenderType

User.objects.filter(gender='non-binary').update(gender=GenderType.OTHERS.value)
