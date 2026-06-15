from django.db import models
from pgvector.django import VectorField
from django.conf import settings


class ExternalManagedModelQuerySet(list):
    def __init__(self, model):
        self.model = model

    def filter(self, **kwargs):
        filtered = [
            obj for obj in self
            if all(getattr(obj, k, None) == v for k, v in kwargs.items())
        ]
        return ExternalManagedModelQuerySet(self.model, filtered)

    def first(self):
        return self[0] if self else None

    def all(self):
        return self

    def order_by(self, *args):
        return self


class ExternalManagedModelManager(models.Manager):
    def get_queryset(self):
        if settings.TEST:
            return self._fake_queryset()
        return super().get_queryset()

    def _fake_queryset(self):
        return ExternalManagedModelQuerySet(self.model, self._mock_data())

    def _mock_data(self):
        return []


class BaseAIModel(models.Model):
    objects = ExternalManagedModelManager()
    class Meta:
        abstract = True
        managed = False


class AIMatchTalentEmbedding(BaseAIModel):
    talent = models.OneToOneField(
        "accounts.Talent",
        db_column="talent_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
    )

    embedding = VectorField(dimensions=384)
    source_hash = models.TextField()

    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "ai_match_talent_embedding"

    def __str__(self):
        return f"Talent Embedding ({self.talent_id})"


class AIMatchJobEmbedding(BaseAIModel):
    job = models.OneToOneField(
        "jobs.Job",
        primary_key=True,
        db_column="job_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
    )

    embedding = VectorField(dimensions=384)
    source_hash = models.TextField()

    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "ai_match_job_embedding"

    def __str__(self):
        return f"Job Embedding ({self.job_id})"


class AIMatchScore(BaseAIModel):
    talent = models.ForeignKey(
        "accounts.Talent",
        db_column="talent_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
    )

    job = models.ForeignKey(
        "jobs.Job",
        db_column="job_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
    )

    raw_cosine = models.FloatField()
    score = models.IntegerField()

    top_percent = models.IntegerField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "ai_match_score"

    def __str__(self):
        return f"{self.talent_id} -> {self.job_id} ({self.score})"


class AIApplicationInsight(BaseAIModel):
    application = models.OneToOneField(
        "jobs.JobApplication",
        db_column="application_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
    )

    talent = models.ForeignKey(
        "accounts.Talent",
        db_column="talent_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
    )

    jobpost = models.ForeignKey(
        "jobs.JobPost",
        db_column="jobpost_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
        null=True,
        blank=True,
    )

    job = models.ForeignKey(
        "jobs.Job",
        db_column="job_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
        null=True,
        blank=True,
    )

    content_hash = models.TextField(
        null=True,
        blank=True,
    )

    model_id = models.TextField(
        null=True,
        blank=True,
    )

    prompt_version = models.TextField(
        null=True,
        blank=True,
    )

    status = models.TextField(
        default="pending",
    )

    summary = models.TextField(
        null=True,
        blank=True,
    )

    strengths = models.JSONField(
        null=True,
        blank=True,
    )

    weaknesses = models.JSONField(
        null=True,
        blank=True,
    )

    red_flags = models.JSONField(
        null=True,
        blank=True,
    )

    raw_output = models.JSONField(
        null=True,
        blank=True,
    )

    error = models.TextField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "ai_application_insight"

    def __str__(self):
        return f"Insight for application {self.application_id}"