import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Department


Department.objects.filter(name="Administration ").update(name="Administration")
print("done updating department")

