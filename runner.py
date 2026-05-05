import os

import django
from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from accounts.models import Department, Role, Business, BusinessUser
from jobs.models import JobPost, Job


def add_roles_to_db():
    roles = "Software development Engineer\nLead Software Engineer\nEngineer I\nEngineer II\nEngineer III\nFrontend Engineer\nBackend Engineer"
    department = "Information Technology (IT)"
    industry = "General Industries"

    department = Department.objects.filter(name__iexact=department, industry__name__iexact=industry).first()
    if department:
        for role in roles.split("\n"):
            role = role.strip()
            role_obj = Role.objects.filter(name__iexact=role, department=department).first()
            if role_obj:
                role_obj.update(name=role)
            else:
                Role.objects.create(name=role, department=department)

def updated_job_and_job_post_created_by():
    print(Job.objects.filter(created_by__isnull=True).count(), "jobs created_by are still null")
    for business in Business.objects.all():
        random_business_user = BusinessUser.objects.filter(business=business).order_by("?").first()
        job_ids = JobPost.objects.filter(Q(recruiter__business=business)|Q(posted_by__business=business)).only("job_id").values_list("job_id", flat=True)
        Job.objects.filter(id__in=job_ids, created_by__isnull=True).update(created_by=random_business_user)
    print(Job.objects.filter(created_by__isnull=True).count(), "jobs created_by are still null")