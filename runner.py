import os

import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Department, Skill


Department.objects.filter(name="Administration ").update(name="Administration")
Skill.objects.filter(name__icontains="frameworks:").update(name="Agile")
Skill.objects.filter(name="").hard_delete()
print("done updating department")

