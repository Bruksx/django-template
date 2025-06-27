from django.contrib import admin
from . import models
from django.contrib import messages


class DepartmentInline(admin.TabularInline):
    model = models.Department
    fields = ["uid", "name"]
    extra = 0


class IndustryAdmin(admin.ModelAdmin):
    inlines = [DepartmentInline, ]


class RoleInline(admin.TabularInline):
    model = models.Role
    fields = ["uid", "name"]
    extra = 0


class DepartmentAdmin(admin.ModelAdmin):
    inlines = [RoleInline, ]


class SkillInline(admin.TabularInline):
    model = models.Skill
    fields = ["uid", "name"]
    extra = 0


class SkillCategoryAdmin(admin.ModelAdmin):
    inlines = [SkillInline, ]


class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'type', 'first_name', 'last_name',)
    search_fields = ('email', 'first_name', 'last_name',)
    ordering = ('-created_at',)

    def get_queryset(self, request):
        return models.User.global_objects.all()

    def delete_model(self, request, obj):
        messages.warning(request, f"Permanently deleting: {obj.email}")
        return obj.hard_delete()
    
    """def delete_queryset(self, request, queryset):
        users = ", ".join(queryset.values_list('email', flat=True))
        messages.warning(request, f"Deleting Users: {users}")
        return queryset.hard_delete()"""



# Register your models here.
admin.site.register(models.Business)
admin.site.register(models.User, UserAdmin)
admin.site.register(models.BusinessUser)
admin.site.register(models.Talent)
admin.site.register(models.Industry, IndustryAdmin)
admin.site.register(models.Department, DepartmentAdmin)
admin.site.register(models.SkillCategory, SkillCategoryAdmin)
admin.site.register(models.Country)