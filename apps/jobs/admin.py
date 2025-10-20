from django.contrib import admin
from .models import (
    EmploymentType, JobPost, JobLevel, Job, BusinessModel, ScreeningQuestion, QuestionOption, JobApplication,
    AvailableDay, RequiredSkill, RequiredAttribute, RequiredSecondaryLanguage, 
)


class RequiredSecondaryLanguageInline(admin.TabularInline):
    model = RequiredSecondaryLanguage
    extra = 0



class RequiredSkillInline(admin.TabularInline):
    model = RequiredSkill
    extra = 0


class RequiredAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "uid",
        "job",
        "role",
        "job_level",
        "years_of_experience",
        "minimum_education_level",
        "work_structure",
        "technological_requirement",
        "first_language",
        "working_hours",
        "location",
    )
    search_fields = ("job__title", "job__uid")
    inlines = [RequiredSecondaryLanguageInline, RequiredSkillInline]


from django.contrib import admin
from .models import JobPost


class JobPostAdmin(admin.ModelAdmin):
    list_display = (
        "uid",
        "job__title",
        "status",
        "country",
    )
    search_fields = (
        "job__uid",
        "uid",
    )


admin.site.register(JobPost, JobPostAdmin)
admin.site.register(EmploymentType)
admin.site.register(JobLevel)
admin.site.register(Job)
admin.site.register(BusinessModel)
admin.site.register(ScreeningQuestion)
admin.site.register(QuestionOption)
admin.site.register(AvailableDay)
admin.site.register(RequiredAttribute, RequiredAttributeAdmin)



@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('id','uid','applicant__user__fullname', 'job_post__job__role__name', 'stage__name')
    search_fields = ('applicant__user__email', 'applicant__user__fullname', "uid", 'job_post__uid')
    list_filter = ('stage__phase', 'deleted_at','stage__created_by__business__name')

    def get_queryset(self, request):
        return JobApplication.global_objects.all()



@admin.register(RequiredSkill)
class RequiredSkillAdmin(admin.ModelAdmin):
    list_display = ("skill__name", "required_attribute__job")
    search_fields = ("required_attribute__job__title", "required_attribute__job__role__name")