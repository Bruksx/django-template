import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Department, Role


def add_roles_to_db():
    roles = "Software development Engineer Lead\nLead Software Engineer\nEngineer I\nEngineer II\nEngineer III\nFrontend Engineer\nBackend Engineer"
    department = "Information Technology (IT)"
    industry = "General Industries"

    department = Department.objects.filter(name__iexact=department, industry__name__iexact=industry).first()
    if department:
        for role in roles.split("\n"):
            role = role.strip().title()
            if not Role.objects.filter(name__iexact=role, department=department).exists():
                Role.objects.create(name=role, department=department)
