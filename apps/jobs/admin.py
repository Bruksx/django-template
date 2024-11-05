from django.contrib import admin
from .models import EmploymentType, JobPost, JobLevel, Job

# Register your models here.
admin.site.register(EmploymentType)
admin.site.register(JobLevel)
admin.site.register(JobPost)
admin.site.register(Job)