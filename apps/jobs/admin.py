from django.contrib import admin
from .models import (
    EmploymentType, JobPost, JobLevel, Job, BusinessModel, ScreeningQuestion, QuestionOption, JobApplication,
    AvailableDay
)

# Register your models here.
admin.site.register(EmploymentType)
admin.site.register(JobLevel)
admin.site.register(JobPost)
admin.site.register(Job)
admin.site.register(BusinessModel)
admin.site.register(ScreeningQuestion)
admin.site.register(QuestionOption)
admin.site.register(JobApplication)
admin.site.register(AvailableDay)