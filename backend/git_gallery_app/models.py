from django.db import models


class Project(models.Model):
    class AnalysisStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        PROCESSING = "processing", "Processing"
        COMPLETE = "complete", "Complete"
        PARTIALLY_COMPLETE = "partially_complete", "Partially Complete"
        FAILED = "failed", "Failed"

    project_name = models.CharField(max_length=200)
    repository_owner = models.CharField(max_length=100)
    repository_name = models.CharField(max_length=100)
    repository_url = models.URLField(max_length=500)
    analysis_status = models.CharField(
        max_length=24,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.NOT_STARTED,
    )
    processed_versions = models.PositiveIntegerField(default=0)
    total_versions = models.PositiveIntegerField(default=0)
    saved_analyses = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "project_name"]

    def __str__(self):
        return f"{self.project_name} ({self.repository_owner}/{self.repository_name})"
