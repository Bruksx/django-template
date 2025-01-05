from django.contrib import admin
from . import models


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



# Register your models here.
admin.site.register(models.Business)
admin.site.register(models.User)
admin.site.register(models.BusinessUser)
admin.site.register(models.Talent)
admin.site.register(models.Industry, IndustryAdmin)
admin.site.register(models.Department, DepartmentAdmin)
admin.site.register(models.SkillCategory, SkillCategoryAdmin)
admin.site.register(models.Country)