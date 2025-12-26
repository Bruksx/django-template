from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from .models import (
    EmploymentType, JobPost, JobLevel, Job, BusinessModel, ScreeningQuestion, QuestionOption, JobApplication,
    AvailableDay, RequiredSkill, RequiredAttribute, RequiredSecondaryLanguage, JobPostExport
)
from .services import export_job_posts_excel


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


class JobPostAdmin(admin.ModelAdmin):
    list_display = (
        "uid",
        "job__uid",
        "job__title",
        "status",
        "country",
    )
    search_fields = (
        "uid",
        "job__uid",
    )

    actions = ["export_all_jobposts",]

    def export_all_jobposts(self, request, queryset):
        export = export_job_posts_excel()
        self.message_user(
            request,
            mark_safe(
                f'Successfully exported job posts'
                f'<a href="{export.file.url}" target="_blank"> Download file</a>'
            ),
            level=messages.SUCCESS,
        )

    export_all_jobposts.short_description = "Export all JobPosts to excel"


admin.site.register(JobPost, JobPostAdmin)
admin.site.register(EmploymentType)
admin.site.register(JobLevel)
admin.site.register(Job)
admin.site.register(BusinessModel)
admin.site.register(ScreeningQuestion)
admin.site.register(QuestionOption)
admin.site.register(AvailableDay)
admin.site.register(RequiredAttribute, RequiredAttributeAdmin)
admin.site.register(JobPostExport)



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