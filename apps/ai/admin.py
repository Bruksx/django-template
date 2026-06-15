from django.contrib import admin

# Register your models here.
from .models import AIMatchTalentEmbedding, AIMatchJobEmbedding, AIMatchScore, AIApplicationInsight


class ReadOnlyAIAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(AIMatchTalentEmbedding)
class AIMatchTalentEmbeddingAdmin(ReadOnlyAIAdmin):
    list_display = ("talent_id",)

    search_fields = ("talent_id", )



@admin.register(AIMatchJobEmbedding)
class AIMatchJobEmbeddingAdmin(ReadOnlyAIAdmin):
    list_display = ("job_id", "updated_at", )

    search_fields = ("job_id", )




@admin.register(AIMatchScore)
class AIMatchScoreAdmin(ReadOnlyAIAdmin):
    list_display = (
        "talent_id",
        "job_id",
        "score",
        "top_percent",
        "updated_at",
    )

    list_filter = ("score", "top_percent")
    search_fields = ("talent_id", "job_id")

    ordering = ("-score",)


@admin.register(AIApplicationInsight)
class AIApplicationInsightAdmin(ReadOnlyAIAdmin):
    list_display = (
        "application_id",
        "talent_id",
        "job_id",
        "status",
        "created_at",
    )

    list_filter = ("status", "created_at")
    search_fields = ("application_id", "talent_id", "job_id", "status")