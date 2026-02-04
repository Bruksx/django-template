import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import BusinessUser
print(BusinessUser.objects.first().user.token)